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

from .config import EPUB_ANALYSIS_VERSION, EPUB_ANALYSIS_WINDOW_SIZE, EPUB_DATABASE, EPUB_DIR, METRIC_ID_BY_FIELD, PUBLICATION_FILE, TEXT_ENCODING, windowed_metric_fields
from .stats import TextStats, compute_stats, punctuation_diversity

FULL_DOCUMENT_FIELDS = {
    "word_count", "sentence_count", "paragraph_count", "avg_word_length", "avg_sentence_length",
    "avg_sentence_word_count", "median_sentence_length", "sentence_length_p10", "sentence_length_p90",
    "paragraph_length_std_dev", "punctuation_per_300_words", "punctuation_diversity", "document_char_count",
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
            "punctuation_per_300_words": len(re.findall(r"[.,;:!?…—–\-()\[\]«»\"]", text)) / word_count * 100 if word_count else 0,
            "punctuation_diversity": punctuation_diversity(text)}


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
    date = metadata.get("publication_date", "")
    year = int(date[:4]) if re.match(r"^\d{4}", date) else 0
    if not date or year < 1500 or year > 2100:
        metadata["publication_date"] = ""
        match = COPYRIGHT_YEAR.search(markdown_body(text))
        if match:
            metadata["publication_date"] = match.group(1)
    return metadata


def publication_overrides() -> dict[str, dict[str, str]]:
    """Lit les corrections manuelles de publication.yml."""
    if not PUBLICATION_FILE.exists():
        return {}
    result = {}
    for line in PUBLICATION_FILE.read_text(encoding=TEXT_ENCODING).splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip().strip('"\'')
        clean_key = key.strip().strip('"\'')
        object_date = re.search(r"\bdate\s*:\s*[\"']([^\"']*)[\"']", value)
        object_title = re.search(r"\btitle\s*:\s*[\"']([^\"']*)[\"']", value)
        result[clean_key] = {"date": object_date.group(1) if object_date else (value if not value.startswith("{") else ""), "title": object_title.group(1) if object_title else ""}
    return result


def publication_date_overrides() -> dict[str, str]:
    return {key: values.get("date", "") for key, values in publication_overrides().items()}


def ensure_publication_date_entries(paths: list[Path]) -> None:
    """Inscrit systématiquement les sources sans date avec une valeur vide."""
    existing = publication_date_overrides()
    missing = []
    for path in paths:
        raw = path.read_text(encoding=TEXT_ENCODING, errors="replace")
        metadata = front_matter(raw)
        # Les Markdown peuvent être autonomes, sans EPUB correspondant.
        key = path.with_suffix(".epub").name if path.with_suffix(".epub").exists() else path.name
        if not metadata.get("publication_date") and key not in existing:
            missing.append(f'{key}: {{date: ""}}')
    if missing:
        PUBLICATION_FILE.parent.mkdir(parents=True, exist_ok=True)
        with PUBLICATION_FILE.open("a", encoding=TEXT_ENCODING) as handle:
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


def analyse_book(connection: sqlite3.Connection, path: Path, author: str | None = None, date_override: str = "", title_override: str = "") -> tuple[bool, int]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    text = raw.decode(TEXT_ENCODING, errors="replace")
    metadata = infer_publication_date(text, front_matter(text))
    if title_override:
        metadata["title"] = title_override
    if date_override:
        metadata["publication_date"] = date_override
    if author:
        metadata["author"] = author
    body = clean_analysis_body(markdown_body(text))
    old = connection.execute("SELECT id, sha256, analysis_version FROM books WHERE path = ?", (str(path),)).fetchone()
    previous_stats = None
    if old is not None and old[1] == digest:
        previous_row = connection.execute("SELECT stats_json FROM analyses WHERE book_id = ? ORDER BY window_index LIMIT 1", (old[0],)).fetchone()
        if previous_row:
            previous_stats = json.loads(previous_row[0])
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
            full_fields = full_document_fields(body)
            # Seules les notes portant {windows} restent limitées à la fenêtre.
            # Toutes les autres mesures viennent du document complet.
            windowed = windowed_metric_fields()
            if previous_stats is not None:
                # Le texte est inchangé : une modification de fenêtre ne doit
                # pas relancer l'analyse spaCy du livre complet.
                metric_values = stats.to_metric_dict()
                for field, identifier in METRIC_ID_BY_FIELD.items():
                    if field not in windowed and identifier in previous_stats:
                        metric_values[identifier] = previous_stats[identifier]
            elif len(windowed) < len(METRIC_ID_BY_FIELD):
                complete = compute_stats(body)
                for field in METRIC_ID_BY_FIELD:
                    if field not in windowed:
                        setattr(stats, field, full_fields.get(field, getattr(complete, field, None)))
            # Les indicateurs de taille et de densité décrivent le livre entier,
            # contrairement aux mesures stylistiques limitées à la première fenêtre.
            for field in FULL_DOCUMENT_FIELDS:
                setattr(stats, field, full_fields[field])
            if previous_stats is None:
                metric_values = stats.to_metric_dict()
            incomplete = [identifier for field, identifier in METRIC_ID_BY_FIELD.items() if metric_values.get(identifier) is None]
            if incomplete:
                raise RuntimeError(f"Analyse incomplète pour {path.name}: {', '.join(incomplete)}")
            connection.execute(
                "INSERT INTO analyses(book_id,window_index,char_start,char_end,char_count,stats_json) VALUES(?,?,?,?,?,?)",
                (book_id, index, start, end, len(fragment), json.dumps(stats.to_metric_dict(), ensure_ascii=False)),
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
    overrides = publication_overrides()
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
            epub_key = path.with_suffix(".epub").name
            correction = overrides.get(epub_key) or overrides.get(path.name, {})
            current_digest = hashlib.sha256(path.read_bytes()).hexdigest()
            previous = connection.execute("SELECT sha256, analysis_version FROM books WHERE path = ?", (str(path),)).fetchone()
            if previous and previous[0] == current_digest and previous[1] == EPUB_ANALYSIS_VERSION:
                print(f"Vérification : {path.name} — déjà à jour", flush=True)
            else:
                reason = "nouveau" if previous is None else ("contenu modifié" if previous[0] != current_digest else "version d’analyse modifiée")
                print(f"Calcul en cours : {path.name} — {reason}", flush=True)
            book_changed, count = analyse_book(connection, path, authors.get(raw_author, raw_author), correction.get("date", ""), correction.get("title", ""))
            connection.commit()
            print(f"{'Calculé' if book_changed else 'Déjà à jour'} : {path.name}", flush=True)
            changed += int(book_changed)
            windows += count
        missing_dates = [row[0] for row in connection.execute("SELECT path FROM books WHERE publication_date = ''")]
        if missing_dates:
            existing = publication_date_overrides()
            additions = []
            for path in missing_dates:
                candidate = Path(path)
                key = candidate.with_suffix(".epub").name if candidate.with_suffix(".epub").exists() else candidate.name
                if key not in existing:
                    additions.append(f'{key}: {{date: ""}}')
            if additions:
                with PUBLICATION_FILE.open("a", encoding=TEXT_ENCODING) as handle:
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
    # Le nombre de fenêtres est une donnée interne de calcul, pas une
    # information utile dans le résumé de la commande.
    with sqlite3.connect(EPUB_DATABASE) as connection:
        missing_dates = [row[0] for row in connection.execute("SELECT path FROM books WHERE publication_date = '' ORDER BY path")]
        unprocessed = [row[0] for row in connection.execute("SELECT books.path FROM books LEFT JOIN analyses ON analyses.book_id = books.id GROUP BY books.id HAVING COUNT(analyses.id) = 0 ORDER BY books.path")]
    if missing_dates:
        print("ATTENTION — sources sans date :")
        for path in missing_dates:
            print(f"  - {Path(path).name} (à compléter dans assets/publication.yml)")
    if unprocessed:
        print("ATTENTION — sources non traitées :")
        for path in unprocessed:
            print(f"  - {Path(path).name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
