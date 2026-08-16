"""Index compact des familles dérivationnelles Démonette 2."""

from collections.abc import Iterable
from contextlib import closing
import csv
import os
import sqlite3
import unicodedata

from .config import DEMONETTE_INDEX, DEMONETTE_LEXEMES, DEMONETTE_SCHEMA_VERSION


def normalize_lexeme(value: str) -> str:
    return unicodedata.normalize("NFC", value.strip().lower().replace("’", "'"))


def _index_is_current() -> bool:
    if not DEMONETTE_INDEX.is_file():
        return False
    try:
        with closing(sqlite3.connect(DEMONETTE_INDEX)) as connection:
            row = connection.execute("SELECT value FROM metadata WHERE key = 'schema_version'").fetchone()
        return bool(row and row[0] == DEMONETTE_SCHEMA_VERSION)
    except sqlite3.Error:
        return False


def ensure_index() -> None:
    if _index_is_current():
        return
    if not DEMONETTE_LEXEMES.is_file():
        raise FileNotFoundError(f"Source Démonette introuvable : {DEMONETTE_LEXEMES}")
    temporary = DEMONETTE_INDEX.with_suffix(".building")
    if temporary.exists():
        temporary.unlink()
    connection = sqlite3.connect(temporary)
    try:
        connection.execute("PRAGMA journal_mode=OFF")
        connection.execute("PRAGMA synchronous=OFF")
        connection.execute("CREATE TABLE families (lexeme TEXT NOT NULL, family TEXT NOT NULL, PRIMARY KEY (lexeme, family))")
        connection.execute("CREATE TABLE pronunciations (form TEXT NOT NULL, phonetic TEXT NOT NULL, PRIMARY KEY (form, phonetic))")
        connection.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        family_batch = []
        phonetic_batch = []
        with DEMONETTE_LEXEMES.open(encoding="utf-8", newline="") as source:
            for row in csv.DictReader(source, delimiter="\t"):
                lexeme = normalize_lexeme(row["graphie"])
                family = row["fid"].strip()
                if lexeme and family:
                    family_batch.append((lexeme, family))
                written = _tagged_values(row.get("para_orth", ""))
                spoken = _tagged_values(row.get("para_phon", ""))
                for tag in written.keys() & spoken.keys():
                    phonetic_batch.extend(
                        (normalize_lexeme(form), phonetic)
                        for form, phonetic in zip(written[tag], spoken[tag])
                        if form and phonetic
                    )
                if len(family_batch) >= 10_000:
                    connection.executemany("INSERT OR IGNORE INTO families VALUES (?, ?)", family_batch)
                    family_batch.clear()
                if len(phonetic_batch) >= 10_000:
                    connection.executemany("INSERT OR IGNORE INTO pronunciations VALUES (?, ?)", phonetic_batch)
                    phonetic_batch.clear()
            if family_batch:
                connection.executemany("INSERT OR IGNORE INTO families VALUES (?, ?)", family_batch)
            if phonetic_batch:
                connection.executemany("INSERT OR IGNORE INTO pronunciations VALUES (?, ?)", phonetic_batch)
        connection.execute("INSERT INTO metadata VALUES ('schema_version', ?)", (DEMONETTE_SCHEMA_VERSION,))
        connection.commit()
    finally:
        connection.close()
    os.replace(temporary, DEMONETTE_INDEX)


def _tagged_values(value: str) -> dict[str, list[str]]:
    result = {}
    for item in value.split(";"):
        tag, separator, values = item.partition(":")
        if separator:
            result.setdefault(tag, []).extend(part for part in values.split("|") if part)
    return result


def family_map(lexemes: Iterable[str]) -> dict[str, frozenset[str]]:
    normalized = sorted({normalize_lexeme(lexeme) for lexeme in lexemes if lexeme})
    if not normalized:
        return {}
    ensure_index()
    result: dict[str, set[str]] = {}
    with closing(sqlite3.connect(DEMONETTE_INDEX)) as connection:
        for start in range(0, len(normalized), 900):
            chunk = normalized[start:start + 900]
            placeholders = ",".join("?" for _ in chunk)
            rows = connection.execute(f"SELECT lexeme, family FROM families WHERE lexeme IN ({placeholders})", chunk)
            for lexeme, family in rows:
                result.setdefault(lexeme, set()).add(family)
    return {lexeme: frozenset(families) for lexeme, families in result.items()}


def phonetic_map(forms: Iterable[str]) -> dict[str, frozenset[str]]:
    normalized = sorted({normalize_lexeme(form) for form in forms if form})
    if not normalized:
        return {}
    ensure_index()
    result: dict[str, set[str]] = {}
    with closing(sqlite3.connect(DEMONETTE_INDEX)) as connection:
        for start in range(0, len(normalized), 900):
            chunk = normalized[start:start + 900]
            placeholders = ",".join("?" for _ in chunk)
            rows = connection.execute(f"SELECT form, phonetic FROM pronunciations WHERE form IN ({placeholders})", chunk)
            for form, phonetic in rows:
                result.setdefault(form, set()).add(phonetic)
    return {form: frozenset(values) for form, values in result.items()}
