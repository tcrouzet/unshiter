"""Index local et lemmatisation déterministe à partir de Morphalou 3.1."""

from collections.abc import Iterable
from contextlib import closing
import csv
import io
import os
import sqlite3
import unicodedata
import zipfile

from .config import (
    MORPHALOU_ARCHIVE,
    MORPHALOU_BATCH_SIZE,
    MORPHALOU_CSV_MEMBER,
    MORPHALOU_INDEX,
    MORPHALOU_SCHEMA_VERSION,
)

_CONTEXTUAL_LEMMA_CACHE: dict[tuple[str, str, str], str] = {}


def normalize_form(value: str) -> str:
    return unicodedata.normalize("NFC", value.strip().lower().replace("’", "'"))


def _edit_distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for left_index, left_character in enumerate(left, 1):
        current = [left_index]
        for right_index, right_character in enumerate(right, 1):
            current.append(min(
                current[-1] + 1,
                previous[right_index] + 1,
                previous[right_index - 1] + (left_character != right_character),
            ))
        previous = current
    return previous[-1]


def _archive_signature() -> str:
    stat = MORPHALOU_ARCHIVE.stat()
    return f"{MORPHALOU_SCHEMA_VERSION}:{stat.st_size}:{stat.st_mtime_ns}"


def _index_is_current() -> bool:
    if not MORPHALOU_INDEX.is_file():
        return False
    try:
        with closing(sqlite3.connect(MORPHALOU_INDEX)) as connection:
            row = connection.execute("SELECT value FROM metadata WHERE key = 'schema_version'").fetchone()
        return bool(row and row[0] == MORPHALOU_SCHEMA_VERSION)
    except sqlite3.Error:
        return False


def ensure_index() -> None:
    if _index_is_current():
        return
    if not MORPHALOU_ARCHIVE.is_file():
        raise FileNotFoundError(f"Archive Morphalou introuvable : {MORPHALOU_ARCHIVE}")
    MORPHALOU_INDEX.parent.mkdir(parents=True, exist_ok=True)
    temporary = MORPHALOU_INDEX.with_suffix(".building")
    if temporary.exists():
        temporary.unlink()
    connection = sqlite3.connect(temporary)
    try:
        connection.execute("PRAGMA journal_mode=OFF")
        connection.execute("PRAGMA synchronous=OFF")
        connection.execute("CREATE TABLE lexicon (form TEXT PRIMARY KEY, lemma TEXT NOT NULL, category TEXT NOT NULL)")
        connection.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        batch: list[tuple[str, str, str]] = []
        current_lemma = ""
        current_category = ""
        with zipfile.ZipFile(MORPHALOU_ARCHIVE) as archive:
            with archive.open(MORPHALOU_CSV_MEMBER) as binary:
                reader = csv.reader(io.TextIOWrapper(binary, encoding="utf-8-sig", newline=""), delimiter=";")
                data_started = False
                for row in reader:
                    if not data_started:
                        data_started = len(row) > 9 and row[0] == "GRAPHIE" and row[9] == "GRAPHIE"
                        continue
                    if len(row) <= 9:
                        continue
                    if row[0].strip():
                        current_lemma = normalize_form(row[0])
                        current_category = row[2].strip()
                    form = normalize_form(row[9])
                    if current_lemma and form:
                        batch.append((form, current_lemma, current_category))
                    if len(batch) >= MORPHALOU_BATCH_SIZE:
                        connection.executemany("INSERT OR IGNORE INTO lexicon VALUES (?, ?, ?)", batch)
                        batch.clear()
                if batch:
                    connection.executemany("INSERT OR IGNORE INTO lexicon VALUES (?, ?, ?)", batch)
        connection.execute("INSERT INTO metadata VALUES ('schema_version', ?)", (MORPHALOU_SCHEMA_VERSION,))
        connection.execute("INSERT INTO metadata VALUES ('archive_signature', ?)", (_archive_signature(),))
        connection.commit()
    finally:
        connection.close()
    os.replace(temporary, MORPHALOU_INDEX)


def lemma_map(forms: Iterable[str]) -> dict[str, str]:
    return {form: data[0] for form, data in lexical_map(forms).items()}


def contextual_lemma_map(items: Iterable[tuple[str, str, str]]) -> dict[str, str]:
    """Combine catégorie contextuelle et familles de flexions Morphalou."""
    normalized_items = [
        (normalize_form(form), category.lower(), normalize_form(suggested))
        for form, category, suggested in items if form
    ]
    forms = sorted({form for form, _, _ in normalized_items})
    if not forms:
        return {}
    ensure_index()
    direct: dict[str, tuple[str, str]] = {}
    with closing(sqlite3.connect(MORPHALOU_INDEX)) as connection:
        for start in range(0, len(forms), 900):
            chunk = forms[start:start + 900]
            placeholders = ",".join("?" for _ in chunk)
            rows = connection.execute(f"SELECT form, lemma, category FROM lexicon WHERE form IN ({placeholders})", chunk)
            for form, lemma, category in rows:
                direct[form] = (lemma, category.lower())
        result = {}
        for form, contextual_category, suggested in normalized_items:
            cache_key = (form, contextual_category, suggested)
            if cache_key in _CONTEXTUAL_LEMMA_CACHE:
                result[form] = _CONTEXTUAL_LEMMA_CACHE[cache_key]
                continue
            stored = direct.get(form)
            if stored and stored[1].startswith(contextual_category):
                result[form] = stored[0]
                _CONTEXTUAL_LEMMA_CACHE[cache_key] = result[form]
                continue
            if suggested and suggested != form:
                result[form] = suggested
                _CONTEXTUAL_LEMMA_CACHE[cache_key] = result[form]
                continue
            inferred = None
            for prefix_length in range(len(form) - 1, 2, -1):
                prefix = form[:prefix_length]
                rows = connection.execute(
                    "SELECT lemma, category FROM lexicon WHERE form >= ? AND form < ?",
                    (prefix, prefix + "\uffff"),
                ).fetchall()
                rows = [row for row in rows if row[1].lower().startswith(contextual_category)]
                if rows:
                    inferred = min((row[0] for row in rows), key=lambda lemma: (_edit_distance(form, lemma), len(lemma), lemma))
                    break
            result[form] = inferred or (stored[0] if stored else suggested or form)
            _CONTEXTUAL_LEMMA_CACHE[cache_key] = result[form]
    return result


def lexical_map(forms: Iterable[str]) -> dict[str, tuple[str, str]]:
    normalized = sorted({normalize_form(form) for form in forms if form})
    if not normalized:
        return {}
    ensure_index()
    result: dict[str, tuple[str, str]] = {}
    with closing(sqlite3.connect(MORPHALOU_INDEX)) as connection:
        for start in range(0, len(normalized), 900):
            chunk = normalized[start:start + 900]
            placeholders = ",".join("?" for _ in chunk)
            rows = connection.execute(f"SELECT form, lemma, category FROM lexicon WHERE form IN ({placeholders})", chunk)
            result.update((form, (lemma, category)) for form, lemma, category in rows)
    return result
