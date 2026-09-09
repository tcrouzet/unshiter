"""Indexe les Markdown issus des EPUB ou déposés directement dans sources."""

from __future__ import annotations

from datetime import datetime, timezone
import argparse
from collections import Counter
import hashlib
import math
import re
import json
import unicodedata
from pathlib import Path
import sqlite3

from .config import (ANALYSIS_WINDOW_WORDS, CORPUS_DIR, DEFAULT_CORPUS_ID,
                     EPUB_ANALYSIS_VERSION, EPUB_DATABASE, METRICS,
                     PERSISTED_METRICS, PUBLICATION_FILE, TEXT_ENCODING,
                     DURATION_MARKERS_FILE)
from .metrics import cached_metric_values, windowed_metric_fields
from .stats import Metrics, WORD_RE, normalize_markdown_text, punctuation_diversity, punctuation_mark_count, punctuation_variety_score, logical_connector_ratio, temporal_connector_ratio

def metric_cache_is_valid(
    connection: sqlite3.Connection,
    book_id: int,
    field: str,
    content_sha256: str,
    window_index: int = 0,
) -> bool:
    """Une mesure est valide si elle existe pour cette version du document."""
    row = connection.execute(
        "SELECT content_sha256 FROM metric_cache "
        "WHERE book_id=? AND window_index=? AND metric_name=?",
        (book_id, window_index, field),
    ).fetchone()
    return bool(row and row[0] == content_sha256)


def invalid_metric_names(
    connection: sqlite3.Connection,
    book_id: int,
    fields: set[str],
    content_sha256: str,
) -> set[str]:
    """Retourne les champs absents ou périmés d'un livre."""
    return {
        field for field in fields
        if not metric_cache_is_valid(connection, book_id, field, content_sha256)
    }


def reset_champ(connection: sqlite3.Connection, field: str, corpus_id: str | None = None) -> int:
    """Invalide un champ ; son absence provoquera son seul recalcul."""
    if field not in METRICS:
        raise ValueError(f"Mesure inconnue : {field}")
    if corpus_id is None:
        cursor = connection.execute("DELETE FROM metric_cache WHERE metric_name=?", (field,))
    else:
        cursor = connection.execute(
            "DELETE FROM metric_cache WHERE metric_name=? AND book_id IN "
            "(SELECT book_id FROM corpus_books WHERE corpus_id=?)",
            (field, corpus_id),
        )
    return cursor.rowcount


def reset_database() -> None:
    """Vide entièrement l'index et les caches sans supprimer le fichier SQLite."""
    EPUB_DATABASE.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(EPUB_DATABASE) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        init_database(connection)
        connection.execute("DELETE FROM metric_cache")
        connection.execute("DELETE FROM analyses")
        connection.execute("DELETE FROM corpus_books")
        connection.execute("DELETE FROM books")
        connection.execute("DELETE FROM corpora")
        connection.commit()
        connection.execute("VACUUM")

FULL_DOCUMENT_FIELDS = {
    "word_count", "sentence_count", "paragraph_count", "avg_word_length", "avg_sentence_length",
    "median_sentence_length", "sentence_length_p10", "sentence_length_p90",
    "paragraph_length_std_dev", "punctuation_ratio", "punctuation_diversity", "document_char_count",
    "dialogue_ratio", "emotion_sentence_ratio",
    "logical_connector_ratio", "temporal_connector_ratio", "scene_summary_ratio", "punctuation_variety_score", "modal_generalization_ratio",
}

def full_document_fields(text: str, max_sentence_length: int | None = None, modal_generalization_value: float = 0.0) -> dict[str, float]:
    words = re.findall(r"[\wÀ-ÿ]+(?:['’][\wÀ-ÿ]+)?", text, flags=re.UNICODE)
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", text) if part.strip()]
    word_count = len(words)
    sentence_lengths = [len(re.findall(r"[\wÀ-ÿ]+", s, flags=re.UNICODE)) for s in sentences]
    paragraph_lengths = [len(re.findall(r"[\wÀ-ÿ]+", p, flags=re.UNICODE)) for p in paragraphs]
    markers = {line.strip().casefold() for line in DURATION_MARKERS_FILE.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")} if DURATION_MARKERS_FILE.exists() else set()
    mean_words = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0
    sorted_lengths = sorted(sentence_lengths)
    percentile = lambda values, q: values[min(len(values) - 1, int(q * (len(values) - 1)))] if values else 0
    para_mean = sum(paragraph_lengths) / len(paragraph_lengths) if paragraph_lengths else 0
    para_std = math.sqrt(sum((n - para_mean) ** 2 for n in paragraph_lengths) / len(paragraph_lengths)) if paragraph_lengths else 0
    dialogue_words = sum(len(re.findall(r"[\wÀ-ÿ]+(?:['’][\wÀ-ÿ]+)?", paragraph)) for paragraph in paragraphs if paragraph.lstrip().startswith(("—", "–", "«")))
    maximum_sentence_length = max_sentence_length or max((len(sentence) for sentence in sentences), default=0)
    scene_scores = [
        float(any(marker in sentence.casefold() for marker in markers))
        * (1 - len(sentence) / maximum_sentence_length)
        if maximum_sentence_length else 0.0
        for sentence in sentences
    ]
    return {"document_char_count": len(text), "word_count": word_count, "sentence_count": len(sentences), "paragraph_count": len(paragraphs),
            "avg_word_length": sum(map(len, words)) / word_count if word_count else 0,
            "avg_sentence_length": mean_words,
            "median_sentence_length": percentile(sorted_lengths, .5), "sentence_length_p10": percentile(sorted_lengths, .1),
            "sentence_length_p90": percentile(sorted_lengths, .9), "paragraph_length_std_dev": para_std,
            "punctuation_mark_count": punctuation_mark_count(text),
            "punctuation_ratio": punctuation_mark_count(text) / word_count if word_count else 0,
            "punctuation_diversity": punctuation_diversity(text),
            "dialogue_ratio": dialogue_words / word_count if word_count else 0,
            "logical_connector_ratio": logical_connector_ratio(text, len(sentences)),
            "temporal_connector_ratio": temporal_connector_ratio(text, len(sentences)),
            "scene_summary_ratio": sum(scene_scores) / len(scene_scores) if scene_scores else 0.0,
            "punctuation_variety_score": punctuation_variety_score(text, len(sentences)),
            "modal_generalization_ratio": modal_generalization_value}


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
    text = normalize_markdown_text(text)
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
        object_author = re.search(r"\bauthor\s*:\s*[\"']([^\"']*)[\"']", value)
        result[clean_key] = {"date": object_date.group(1) if object_date else (value if not value.startswith("{") else ""), "title": object_title.group(1) if object_title else "", "author": object_author.group(1) if object_author else ""}
    return result


def canonical_authors(values: list[str], preferred: set[str] | None = None) -> dict[str, str]:
    """Regroupe les formes incomplètes ou permutées d'un même auteur.

    Lorsqu'un nom est contenu dans une forme plus complète (``Caza`` dans
    ``Philippe Caza``), la forme complète devient la référence. Les formes
    prénom/nom permutées continuent également d'être réunies.
    """
    present = {value.strip() for value in values if value.strip()}
    preferred = preferred or set()
    ordered = {value: index for index, value in enumerate(values)}
    frequencies = Counter(values)
    result = {}
    for value in present:
        parts = value.split()
        permutation = " ".join(reversed(parts)) if len(parts) == 2 else ""
        normalized_tokens = frozenset(re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()))
        equivalent = [candidate for candidate in present if frozenset(re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKD", candidate).encode("ascii", "ignore").decode().lower())) == normalized_tokens]
        if len(equivalent) > 1:
            result[value] = max(equivalent, key=lambda candidate: (frequencies[candidate], len(candidate)))
            continue
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
    # Une forme abrégée est rattachée à la forme complète disponible.
    # On compare les mots normalisés, sans imposer de cas particulier à un
    # auteur : tout nom dont les tokens sont un sous-ensemble est concerné.
    for value in present:
        tokens = set(re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()))
        candidates = []
        for candidate in present:
            candidate_tokens = set(re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKD", candidate).encode("ascii", "ignore").decode().lower()))
            if candidate != value and tokens and tokens < candidate_tokens:
                candidates.append(candidate)
        if candidates:
            result[value] = max(candidates, key=lambda candidate: (len(candidate.split()), -ordered.get(candidate, 10**9)))
    return result


def canonicalize_database_authors(connection: sqlite3.Connection) -> None:
    rows = connection.execute("SELECT author, MIN(id) FROM books WHERE author <> '' GROUP BY author ORDER BY MIN(id)").fetchall()
    ordered = [row[0] for row in rows]
    mapping = canonical_authors(ordered)
    for source, target in mapping.items():
        if source != target:
            connection.execute("UPDATE books SET author=? WHERE author=?", (target, source))


def word_windows(text: str, size: int = ANALYSIS_WINDOW_WORDS) -> list[tuple[int, int, str]]:
    """Découpe le texte en fenêtres contiguës de *size* mots."""
    if not text:
        return []
    matches = list(WORD_RE.finditer(text))
    if not matches:
        return []
    windows = []
    for first in range(0, len(matches), size):
        start = 0 if first == 0 else matches[first].start()
        following = first + size
        end = matches[following].start() if following < len(matches) else len(text)
        fragment = text[start:end].strip()
        if fragment:
            windows.append((start, end, fragment))
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
            UNIQUE(book_id, window_index)
        );
        CREATE INDEX IF NOT EXISTS analyses_book_idx ON analyses(book_id);
        CREATE TABLE IF NOT EXISTS metric_cache (
            book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
            window_index INTEGER NOT NULL,
            metric_name TEXT NOT NULL,
            value_json TEXT NOT NULL,
            content_sha256 TEXT NOT NULL,
            function_hash TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(book_id, window_index, metric_name)
        );
        CREATE INDEX IF NOT EXISTS metric_cache_book_idx ON metric_cache(book_id);
        CREATE TABLE IF NOT EXISTS corpora (
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS corpus_books (
            corpus_id TEXT NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
            book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
            PRIMARY KEY(corpus_id, book_id)
        );
        CREATE INDEX IF NOT EXISTS corpus_books_book_idx ON corpus_books(book_id);
        """
    )
    cache_columns = {row[1] for row in connection.execute("PRAGMA table_info(metric_cache)")}
    if "metric_id" in cache_columns and "metric_name" not in cache_columns:
        connection.execute("ALTER TABLE metric_cache RENAME COLUMN metric_id TO metric_name")
    # Les anciens identifiants numériques ne sont plus interprétés : leur
    # suppression provoque le recalcul partiel normal, sous le nom de méthode.
    connection.execute("DELETE FROM metric_cache WHERE metric_name GLOB 'mesure_[0-9]*'")
    columns = {row[1] for row in connection.execute("PRAGMA table_info(books)")}
    if "analysis_version" not in columns:
        connection.execute("ALTER TABLE books ADD COLUMN analysis_version TEXT NOT NULL DEFAULT ''")
    # Migration sans recalcul : les anciennes analyses sont décomposées une
    # seule fois dans le cache individuel dès que la base est ouverte.
    analysis_columns = {row[1] for row in connection.execute("PRAGMA table_info(analyses)")}
    if "stats_json" in analysis_columns:
        rows = connection.execute(
            "SELECT a.book_id, a.window_index, a.stats_json, b.sha256 "
            "FROM analyses a JOIN books b ON b.id = a.book_id"
        ).fetchall()
        for book_id, window_index, stats_json, digest in rows:
            try:
                values = json.loads(stats_json)
            except (TypeError, json.JSONDecodeError):
                continue
            connection.executemany(
                "INSERT OR IGNORE INTO metric_cache(book_id,window_index,metric_name,value_json,content_sha256,function_hash,updated_at) VALUES(?,?,?,?,?,?,?)",
                [
                    (book_id, window_index, metric_id, json.dumps(value, ensure_ascii=False), digest, "", datetime.now(timezone.utc).isoformat())
                    for metric_id, value in values.items()
                ],
            )
        connection.execute("ALTER TABLE analyses DROP COLUMN stats_json")
    # SQLite ne conserve que les données élémentaires. Les ratios, densités
    # et scores composites sont reconstruits depuis ces valeurs persistées.
    placeholders = ",".join("?" for _ in PERSISTED_METRICS)
    connection.execute(
        f"DELETE FROM metric_cache WHERE metric_name NOT IN ({placeholders})",
        tuple(PERSISTED_METRICS),
    )
    connection.execute("INSERT OR IGNORE INTO corpora(id,label) VALUES(?,?)", ("bigcorpus", "bigcorpus"))
    project_root = CORPUS_DIR.parent
    connection.execute(
        "UPDATE books SET path=replace(path, ?, ?) WHERE path LIKE ?",
        (str(project_root / "_epub"), str(CORPUS_DIR / "bigcorpus" / "_epub"), str(project_root / "_epub") + "/%"),
    )
    connection.execute(
        "UPDATE books SET path=replace(path, ?, ?) WHERE path LIKE ?",
        (str(project_root / "sources"), str(CORPUS_DIR / "bigcorpus" / "sources"), str(project_root / "sources") + "/%"),
    )
    connection.execute(
        "INSERT OR IGNORE INTO corpus_books(corpus_id,book_id) "
        "SELECT 'bigcorpus',id FROM books WHERE path LIKE ?",
        (str(CORPUS_DIR / "bigcorpus") + "/%",),
    )


def analyse_book(connection: sqlite3.Connection, path: Path, author: str | None = None, date_override: str = "", title_override: str = "", corpus_max_sentence_length: int | None = None, progress=None) -> tuple[bool, int, int]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    text = raw.decode(TEXT_ENCODING, errors="replace")
    metadata = infer_publication_date(text, front_matter(text))
    # Un Markdown autonome ne dispose pas forcément de métadonnées YAML.
    # Son nom de fichier constitue alors le seul titre fiable disponible.
    if not metadata.get("title"):
        metadata["title"] = path.stem
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
        previous_stats = cached_metric_values(connection, old[0])
    # Le front matter Markdown est la référence de secours lorsqu'un EPUB ne
    # fournit pas de créateur exploitable. Pour un livre déjà indexé, on
    # conserve aussi son auteur au lieu de l'effacer lors d'une régénération.
    if not metadata.get("author") and old is not None:
        previous = connection.execute("SELECT author FROM books WHERE id = ?", (old[0],)).fetchone()
        if previous and previous[0]:
            metadata["author"] = previous[0]
    required_metric_ids = set(PERSISTED_METRICS)
    if old is not None and old[1] == digest:
        missing_metric_ids = invalid_metric_names(connection, old[0], required_metric_ids, digest)
        # Une valeur périmée ne peut pas être réinjectée comme donnée partagée
        # pendant le recalcul d'un score composite.
        for field in missing_metric_ids:
            if previous_stats is not None:
                previous_stats.pop(field, None)
    else:
        missing_metric_ids = required_metric_ids
    full_recompute = old is None or old[1] != digest or old[2] != EPUB_ANALYSIS_VERSION
    changed = full_recompute or bool(missing_metric_ids)
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
        if full_recompute:
            connection.execute("DELETE FROM analyses WHERE book_id = ?", (book_id,))
            connection.execute("DELETE FROM metric_cache WHERE book_id = ?", (book_id,))
        windows = word_windows(body)[:1]
        for index, (start, end, fragment) in enumerate(windows):
            connection.execute(
                "INSERT INTO analyses(book_id,window_index,char_start,char_end,char_count) VALUES(?,?,?,?,?) "
                "ON CONFLICT(book_id,window_index) DO UPDATE SET "
                "char_start=excluded.char_start,char_end=excluded.char_end,char_count=excluded.char_count",
                (book_id, index, start, end, len(fragment)),
            )
            windowed = windowed_metric_fields()
            # Les composites peuvent réutiliser leurs composantes déjà
            # persistées sans relancer spaCy ni les calculs structurels.
            window_metrics = Metrics(fragment, progress=progress, shared_metrics=previous_stats)
            document_metrics = Metrics(body, progress=progress, shared_metrics=previous_stats)
            requested = set(PERSISTED_METRICS) if full_recompute else missing_metric_ids
            total = len(requested)
            step = 0
            # METRICS est l'unique plan de génération. En mode partiel, les
            # méthodes associées aux valeurs présentes ne sont jamais appelées.
            for field in METRICS:
                if field not in requested:
                    continue
                step += 1
                source = window_metrics if field in windowed else document_metrics
                value = getattr(source, field)()
                if value is None and field in {"negation_completeness_ratio", "periphrastic_future_ratio"}:
                    value = 0
                if value is None:
                    raise RuntimeError(f"Analyse incomplète pour {path.name}: {field}")
                # Écriture immédiate : une mesure validée est persistée avant
                # que la suivante soit demandée.
                connection.execute(
                    "INSERT OR REPLACE INTO metric_cache(book_id,window_index,metric_name,value_json,content_sha256,function_hash,updated_at) VALUES(?,?,?,?,?,?,?)",
                    (book_id, index, field, json.dumps(value, ensure_ascii=False), digest,
                     "", datetime.now(timezone.utc).isoformat()),
                )
                if progress:
                    progress(step, total, field)
    else:
        windows = connection.execute("SELECT id FROM analyses WHERE book_id = ?", (book_id,)).fetchall()
    return changed, len(windows), book_id


def build_database(paths: list[Path] | None = None, corpus_id: str = DEFAULT_CORPUS_ID, complete_existing: bool = False) -> tuple[int, int]:
    EPUB_DATABASE.parent.mkdir(parents=True, exist_ok=True)
    synchronize = paths is None
    if paths is None:
        # La base regroupe les livres extraits des EPUB et les Markdown
        # autonomes déposés dans sources. Un même fichier n'est indexé
        # qu'une fois si les deux répertoires contiennent le même chemin.
        corpus_root = CORPUS_DIR / corpus_id
        # L'organisation interne est libre : tous les Markdown situés sous
        # le dossier du corpus lui appartiennent, quelle que soit la profondeur.
        discovered = set(corpus_root.rglob("*.md"))
        paths = sorted(discovered)
    paths = [path.resolve() for path in paths]
    metadata_by_path = {}
    overrides = publication_overrides()
    for path in paths:
        raw = path.read_text(encoding=TEXT_ENCODING, errors="replace")
        metadata = front_matter(raw)
        key = path.with_suffix(".epub").name if path.with_suffix(".epub").exists() else path.name
        override_author = overrides.get(key, {}).get("author", "")
        if override_author:
            metadata["author"] = override_author
        metadata_by_path[path] = metadata
    with sqlite3.connect(EPUB_DATABASE) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        init_database(connection)
        connection.execute("INSERT OR IGNORE INTO corpora(id,label) VALUES(?,?)", (corpus_id, corpus_id))
        connection.commit()
        canonicalize_database_authors(connection)
        existing_authors = set(row[0] for row in connection.execute("SELECT DISTINCT author FROM books") if row[0])
        authors = canonical_authors([metadata.get("author", "") for metadata in metadata_by_path.values()], existing_authors)
        if synchronize:
            connection.execute("DELETE FROM corpus_books WHERE corpus_id=?", (corpus_id,))
            connection.commit()
        # Le dénominateur de la mesure de sommaire est le maximum de longueur
        # de phrase observé dans tout le corpus, identique pour chaque livre.
        corpus_max_sentence_length = 0
        total_paths = len(paths)
        for index, path in enumerate(paths, 1):
            body = clean_analysis_body(markdown_body(path.read_text(encoding=TEXT_ENCODING, errors="replace")))
            corpus_sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", body) if part.strip()]
            corpus_max_sentence_length = max(corpus_max_sentence_length, *(len(sentence) for sentence in corpus_sentences)) if corpus_sentences else corpus_max_sentence_length
        changed = windows = 0
        for index, path in enumerate(paths, 1):
            raw_author = metadata_by_path[path].get("author", "")
            epub_key = path.with_suffix(".epub").name
            correction = overrides.get(epub_key) or overrides.get(path.name, {})
            current_digest = hashlib.sha256(path.read_bytes()).hexdigest()
            previous = connection.execute("SELECT sha256, analysis_version FROM books WHERE path = ?", (str(path),)).fetchone()
            book_row = connection.execute("SELECT id FROM books WHERE path=?", (str(path),)).fetchone()
            invalid_fields = invalid_metric_names(
                connection, book_row[0], set(PERSISTED_METRICS), current_digest,
            ) if book_row and previous and previous[0] == current_digest else set(PERSISTED_METRICS)
            if previous and previous[0] == current_digest and previous[1] == EPUB_ANALYSIS_VERSION and not invalid_fields:
                print(f"[{index}/{total_paths}] Vérification : {path.name} — déjà à jour", flush=True)
            else:
                reason = "nouveau" if previous is None else ("contenu modifié" if previous[0] != current_digest else ("mesure absente ou calcul modifié" if invalid_fields else "version d’analyse modifiée"))
                print(f"[{index}/{total_paths}] Calcul en cours : {path.name} — {reason}", flush=True)
            def show_analysis_progress(step, total, label, *, _index=index, _path=path):
                width = 20
                filled = round(width * step / total)
                bar = "█" * filled + "░" * (width - filled)
                print(f"\r    [{_index}/{total_paths}] {bar} {step * 100 // total:3d}% — {label}", end="", flush=True)
                if step >= total:
                    print(flush=True)

            book_changed, count, book_id = analyse_book(connection, path, authors.get(raw_author, raw_author), correction.get("date", ""), correction.get("title", ""), corpus_max_sentence_length, show_analysis_progress)
            connection.execute("INSERT OR IGNORE INTO corpus_books(corpus_id,book_id) VALUES(?,?)", (corpus_id, book_id))
            connection.commit()
            print(f"[{index}/{total_paths}] {'Calculé' if book_changed else 'Déjà à jour'} : {path.name}", flush=True)
            changed += int(book_changed)
            windows += count
        # Harmonise aussi les lignes conservées après la synchronisation :
        # cela supprime les groupes fantômes créés par « Nom Prénom » /
        # « Prénom Nom ».
        canonicalize_database_authors(connection)
        connection.commit()
    return changed, windows


def main() -> int:
    parser = argparse.ArgumentParser(description="Indexe les Markdown et calcule leurs statistiques")
    parser.add_argument("--reset-only", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--reset-champ", action="append", choices=tuple(METRICS), metavar="MESURE",
        help="invalide ce champ dans toute la base avant son recalcul (option répétable)",
    )
    parser.add_argument("--corpus", default=DEFAULT_CORPUS_ID, help="identifiant du dossier dans corpus/ (crouzet par défaut en développement)")
    parser.add_argument("--complete", action="store_true", help="calcule les mesures manquantes des œuvres déjà analysées dans un autre corpus")
    parser.add_argument("paths", nargs="*", type=Path, help="Markdown à traiter ; sans argument, ceux de _epub et sources")
    args = parser.parse_args()
    if args.reset_only:
        reset_database()
        print(f"Base entièrement réinitialisée : {EPUB_DATABASE}")
        return 0
    if args.reset_champ:
        with sqlite3.connect(EPUB_DATABASE) as connection:
            init_database(connection)
            for field in args.reset_champ:
                reset_champ(connection, field)
            connection.commit()
    changed, windows = build_database(args.paths or None, args.corpus, args.complete)
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
