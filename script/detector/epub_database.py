"""Indexe les livres EPUB convertis en Markdown et calcule leurs statistiques."""

from __future__ import annotations

from datetime import datetime, timezone
import argparse
import hashlib
import math
import re
import json
from pathlib import Path
import re
import sqlite3

from .config import EPUB_ANALYSIS_VERSION, EPUB_ANALYSIS_WINDOW_SIZE, EPUB_DATABASE, EPUB_DIR, PUBLICATION_DATES_FILE, TEXT_ENCODING
from .stats import TextStats, compute_stats

FULL_DOCUMENT_FIELDS = {
    "word_count", "sentence_count", "paragraph_count", "avg_word_length", "avg_sentence_length",
    "avg_sentence_word_count", "median_sentence_length", "sentence_length_p10", "sentence_length_p90",
    "paragraph_length_std_dev", "punctuation_per_300_words", "document_char_count",
}

def full_document_fields(text: str) -> dict[str, float]:
    words = re.findall(r"[\wÀ-ÿ]+(?:['’][\wÀ-ÿ]+)?", text, flags=re.UNICODE)
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", text) if part.strip()]
    word_count = len(words)
    sentence_lengths = [len(re.findall(r"[\wÀ-ÿ]+", s, flags=re.UNICODE)) for s in sentences]
    sentence_chars = [len(s) for s in sentences]
    paragraph_lengths = [len(re.findall(r"[\wÀ-ÿ]+", p, flags=re.UNICODE)) for p in paragraphs]
    mean_chars = sum(sentence_chars) / len(sentence_chars) if sentence_chars else 0
    mean_words = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0
    sorted_chars = sorted(sentence_chars)
    percentile = lambda values, q: values[min(len(values) - 1, int(q * (len(values) - 1)))] if values else 0
    para_mean = sum(paragraph_lengths) / len(paragraph_lengths) if paragraph_lengths else 0
    para_std = math.sqrt(sum((n - para_mean) ** 2 for n in paragraph_lengths) / len(paragraph_lengths)) if paragraph_lengths else 0
    return {"document_char_count": len(text), "word_count": word_count, "sentence_count": len(sentences), "paragraph_count": len(paragraphs),
            "avg_word_length": sum(map(len, words)) / word_count if word_count else 0,
            "avg_sentence_length": mean_chars, "avg_sentence_word_count": mean_words,
            "median_sentence_length": percentile(sorted_chars, .5), "sentence_length_p10": percentile(sorted_chars, .1),
            "sentence_length_p90": percentile(sorted_chars, .9), "paragraph_length_std_dev": para_std,
            "punctuation_per_300_words": len(re.findall(r"[,;:!?—()\[\]…]", text)) / word_count * 300 if word_count else 0}


SENTENCE_END = re.compile(r"[.!?…]+[\"»”’'\)\]]*(?=\s|$)")
COPYRIGHT_YEAR = re.compile(r"(?:©|copyright|droits réservés|tous droits)[^\n]{0,180}?\b((?:19|20)\d{2})\b", re.I)


def markdown_body(text: str) -> str:
    """Retire le front matter YAML avant l'analyse stylistique."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end >= 0:
            return text[end + 4:].lstrip("\n")
    return text


def clean_analysis_body(text: str) -> str:
    """Retire les titres, citations et sections liminaires."""
    preliminary = ("préface", "avant-propos", "prologue", "prélude", "introduction", "mentions légales", "dédicace", "exergue")
    result = []
    skip_section = False
    for line in text.splitlines():
        heading = re.match(r"^\s*#{1,6}\s+(.+?)\s*$", line)
        if heading:
            skip_section = any(word in heading.group(1).casefold() for word in preliminary)
            continue
        if skip_section or re.match(r"^\s*>\s?", line):
            continue
        result.append(line)
    return "\n".join(result).strip()


def front_matter(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    if not text.startswith("---"):
        return values
    end = text.find("\n---", 3)
    if end < 0:
        return values
    for line in text[4:end].splitlines():
        key, separator, value = line.partition(":")
        if separator:
            values[key.strip()] = value.strip().strip('"')
    return values


def infer_publication_date(text: str, metadata: dict[str, str]) -> dict[str, str]:
    """Complète une date absente avec une année explicitement imprimée."""
    if not metadata.get("publication_date"):
        match = COPYRIGHT_YEAR.search(markdown_body(text))
        if match:
            metadata["publication_date"] = match.group(1)
    return metadata


def publication_date_overrides() -> dict[str, str]:
    """Lit les dates manuelles, sans imposer de dépendance YAML au programme."""
    if not PUBLICATION_DATES_FILE.exists():
        return {}
    result = {}
    for line in PUBLICATION_DATES_FILE.read_text(encoding=TEXT_ENCODING).splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip().strip('"\'')] = value.strip().strip('"\'')
    return result


def ensure_publication_date_entries(paths: list[Path]) -> None:
    """Inscrit systématiquement les sources sans date avec une valeur vide."""
    existing = publication_date_overrides()
    missing = []
    for path in paths:
        metadata = infer_publication_date(path.read_text(encoding=TEXT_ENCODING, errors="replace"), front_matter(path.read_text(encoding=TEXT_ENCODING, errors="replace")))
        key = path.with_suffix(".epub").name
        if not metadata.get("publication_date") and key not in existing:
            missing.append(f'{key}: ""')
    if missing:
        PUBLICATION_DATES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with PUBLICATION_DATES_FILE.open("a", encoding=TEXT_ENCODING) as handle:
            handle.write("\n" + "\n".join(missing) + "\n")


def canonical_authors(values: list[str], preferred: set[str] | None = None) -> dict[str, str]:
    """Utilise une forme déjà présente lorsqu'un nom/prénom est permuté."""
    present = {value.strip() for value in values if value.strip()}
    preferred = preferred or set()
    ordered = {value: index for index, value in enumerate(values)}
    result = {}
    for value in present:
        parts = value.split()
        permutation = " ".join(reversed(parts)) if len(parts) == 2 else ""
        # Une forme déjà validée dans la base reste prioritaire. On ne doit
        # jamais la retourner vers sa permutation simplement parce que celle-ci
        # apparaît aussi dans un nouveau front matter.
        if value in preferred:
            result[value] = value
        elif permutation in preferred:
            result[value] = permutation
        elif permutation in present and ordered.get(permutation, 10**9) < ordered.get(value, 10**9):
            result[value] = permutation
        else:
            result[value] = value
    return result


def canonicalize_database_authors(connection: sqlite3.Connection) -> None:
    rows = connection.execute("SELECT author, MIN(id) FROM books WHERE author <> '' GROUP BY author ORDER BY MIN(id)").fetchall()
    ordered = [row[0] for row in rows]
    mapping = canonical_authors(ordered)
    for source, target in mapping.items():
        if source != target:
            connection.execute("UPDATE books SET author=? WHERE author=?", (target, source))


def character_windows(text: str, size: int = EPUB_ANALYSIS_WINDOW_SIZE) -> list[tuple[int, int, str]]:
    """Découpe en fenêtres contiguës d'environ *size* signes, finies sur une phrase."""
    if not text:
        return []
    windows = []
    start = 0
    while start < len(text):
        target = min(start + size, len(text))
        if target == len(text):
            end = target
        else:
            match = SENTENCE_END.search(text, target)
            end = match.end() if match else len(text)
        fragment = text[start:end].strip()
        if fragment:
            windows.append((start, end, fragment))
        start = end
    return windows


def init_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL DEFAULT '',
            author TEXT NOT NULL DEFAULT '',
            publisher TEXT NOT NULL DEFAULT '',
            publication_date TEXT NOT NULL DEFAULT '',
            size INTEGER NOT NULL DEFAULT 0,
            sha256 TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            analysis_version TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY,
            book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
            window_index INTEGER NOT NULL,
            char_start INTEGER NOT NULL,
            char_end INTEGER NOT NULL,
            char_count INTEGER NOT NULL,
            stats_json TEXT NOT NULL,
            UNIQUE(book_id, window_index)
        );
        CREATE INDEX IF NOT EXISTS analyses_book_idx ON analyses(book_id);
        """
    )
    columns = {row[1] for row in connection.execute("PRAGMA table_info(books)")}
    if "analysis_version" not in columns:
        connection.execute("ALTER TABLE books ADD COLUMN analysis_version TEXT NOT NULL DEFAULT ''")


def analyse_book(connection: sqlite3.Connection, path: Path, author: str | None = None, date_override: str = "") -> tuple[bool, int]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    text = raw.decode(TEXT_ENCODING, errors="replace")
    metadata = infer_publication_date(text, front_matter(text))
    if not metadata.get("publication_date") and date_override:
        metadata["publication_date"] = date_override
    if author:
        metadata["author"] = author
    body = clean_analysis_body(markdown_body(text))
    old = connection.execute("SELECT id, sha256, analysis_version FROM books WHERE path = ?", (str(path),)).fetchone()
    # Le front matter Markdown est la référence de secours lorsqu'un EPUB ne
    # fournit pas de créateur exploitable. Pour un livre déjà indexé, on
    # conserve aussi son auteur au lieu de l'effacer lors d'une régénération.
    if not metadata.get("author") and old is not None:
        previous = connection.execute("SELECT author FROM books WHERE id = ?", (old[0],)).fetchone()
        if previous and previous[0]:
            metadata["author"] = previous[0]
    changed = old is None or old[1] != digest or old[2] != EPUB_ANALYSIS_VERSION
    now = datetime.now(timezone.utc).isoformat()
    if old is None:
        cursor = connection.execute(
            "INSERT INTO books(path,title,author,publisher,publication_date,size,sha256,updated_at,analysis_version) VALUES(?,?,?,?,?,?,?,?,?)",
            (str(path), metadata.get("title", ""), metadata.get("author", ""), metadata.get("publisher", ""), metadata.get("publication_date", ""), len(body), digest, now, EPUB_ANALYSIS_VERSION),
        )
        book_id = cursor.lastrowid
        changed = True
    else:
        book_id = old[0]
        connection.execute(
            "UPDATE books SET title=?, author=?, publisher=?, publication_date=?, size=?, sha256=?, updated_at=?, analysis_version=? WHERE id=?",
            (metadata.get("title", ""), metadata.get("author", ""), metadata.get("publisher", ""), metadata.get("publication_date", ""), len(body), digest, now, EPUB_ANALYSIS_VERSION, book_id),
        )
    if changed:
        connection.execute("DELETE FROM analyses WHERE book_id = ?", (book_id,))
        windows = character_windows(body)[:1]
        for index, (start, end, fragment) in enumerate(windows):
            stats: TextStats = compute_stats(fragment)
            # Les indicateurs de taille et de densité décrivent le livre entier,
            # contrairement aux mesures stylistiques limitées à la première fenêtre.
            full_fields = full_document_fields(body)
            for field in FULL_DOCUMENT_FIELDS:
                setattr(stats, field, full_fields[field])
            connection.execute(
                "INSERT INTO analyses(book_id,window_index,char_start,char_end,char_count,stats_json) VALUES(?,?,?,?,?,?)",
                (book_id, index, start, end, len(fragment), json.dumps(stats.to_dict(), ensure_ascii=False)),
            )
    else:
        windows = connection.execute("SELECT id FROM analyses WHERE book_id = ?", (book_id,)).fetchall()
    return changed, len(windows)


def build_database(paths: list[Path] | None = None) -> tuple[int, int]:
    EPUB_DATABASE.parent.mkdir(parents=True, exist_ok=True)
    synchronize = paths is None
    paths = [path.resolve() for path in (paths or sorted(EPUB_DIR.glob("*.md")))]
    ensure_publication_date_entries(paths)
    metadata_by_path = {}
    date_overrides = publication_date_overrides()
    for path in paths:
        raw = path.read_text(encoding=TEXT_ENCODING, errors="replace")
        metadata_by_path[path] = front_matter(raw)
    with sqlite3.connect(EPUB_DATABASE) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        init_database(connection)
        connection.commit()
        canonicalize_database_authors(connection)
        existing_authors = set(row[0] for row in connection.execute("SELECT DISTINCT author FROM books") if row[0])
        authors = canonical_authors([metadata.get("author", "") for metadata in metadata_by_path.values()], existing_authors)
        if synchronize:
            current_paths = {str(path) for path in paths}
            if current_paths:
                connection.execute(
                    "DELETE FROM books WHERE path NOT IN ({})".format(",".join("?" for _ in current_paths)),
                    tuple(current_paths),
                )
            else:
                connection.execute("DELETE FROM books")
            connection.commit()
        changed = windows = 0
        for path in paths:
            raw_author = metadata_by_path[path].get("author", "")
            book_changed, count = analyse_book(connection, path, authors.get(raw_author, raw_author), date_overrides.get(path.with_suffix(".epub").name, ""))
            connection.commit()
            print(f"{'Calculé' if book_changed else 'Déjà à jour'} : {path.name} ({count} fenêtre)")
            changed += int(book_changed)
            windows += count
        missing_dates = [row[0] for row in connection.execute("SELECT path FROM books WHERE publication_date = ''")]
        if missing_dates:
            existing = publication_date_overrides()
            additions = [f'{Path(path).with_suffix(".epub").name}: ""' for path in missing_dates if Path(path).with_suffix(".epub").name not in existing]
            if additions:
                with PUBLICATION_DATES_FILE.open("a", encoding=TEXT_ENCODING) as handle:
                    handle.write("\n" + "\n".join(additions) + "\n")
        # Harmonise aussi les lignes conservées après la synchronisation :
        # cela supprime les groupes fantômes créés par « Nom Prénom » /
        # « Prénom Nom ».
        canonicalize_database_authors(connection)
        connection.commit()
    return changed, windows


def main() -> int:
    parser = argparse.ArgumentParser(description="Indexe les Markdown issus des EPUB et calcule leurs statistiques")
    parser.add_argument("paths", nargs="*", type=Path, help="Markdown EPUB à traiter ; sans argument, tous ceux de _epub")
    args = parser.parse_args()
    changed, windows = build_database(args.paths or None)
    print(f"Base : {EPUB_DATABASE}")
    print(f"Livres recalculés : {changed}")
    print(f"Fenêtres analysées : {windows} ({EPUB_ANALYSIS_WINDOW_SIZE} signes cible)")
    with sqlite3.connect(EPUB_DATABASE) as connection:
        missing_dates = [row[0] for row in connection.execute("SELECT path FROM books WHERE publication_date = '' ORDER BY path")]
        unprocessed = [row[0] for row in connection.execute("SELECT books.path FROM books LEFT JOIN analyses ON analyses.book_id = books.id GROUP BY books.id HAVING COUNT(analyses.id) = 0 ORDER BY books.path")]
    if missing_dates:
        print("ATTENTION — EPUB sans date :")
        for path in missing_dates:
            print(f"  - {Path(path).name} (à compléter dans assets/publication-dates.yml)")
    if unprocessed:
        print("ATTENTION — EPUB non traités :")
        for path in unprocessed:
            print(f"  - {Path(path).name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
