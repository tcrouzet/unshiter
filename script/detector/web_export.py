"""Exporte la base SQLite vers les données statiques du site web."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sqlite3

from .config import (ANALYSIS_WINDOW_WORDS, BIGFIVE_AXES, EPUB_DATABASE, METRICS, RAW_METRICS,
                     SITE_CONFIG_FILE, TEXT_ENCODING, WEB_DATA_FILE,
                     CLASSICISM_WEIGHTS, ORNATENESS_WEIGHTS,
                     NARRATIVITY_WEIGHTS, EMOTIONALITY_WEIGHTS,
                     DISCURSIVITE_WEIGHTS)
from .config import CHART_PALETTE_FILE, STATS_NOTES_FILE
from .metrics import cached_metric_values


def site_config() -> dict[str, str]:
    values = {"name": "Site Unshiter", "author": "Thierry Crouzet", "author_url": "https://tcrouzet.com", "description": "", "copyright": "© {author} — (date) — {livres} livres"}
    if SITE_CONFIG_FILE.exists():
        for line in SITE_CONFIG_FILE.read_text(encoding=TEXT_ENCODING).splitlines():
            key, separator, value = line.partition(":")
            if separator and key.strip() in values:
                values[key.strip()] = value.strip().strip('"\'')
    return values


def chart_palette() -> dict[str, str]:
    result = {}
    if CHART_PALETTE_FILE.exists():
        for line in CHART_PALETTE_FILE.read_text(encoding=TEXT_ENCODING).splitlines():
            key, separator, value = line.partition(":")
            if separator and key.strip() and value.strip():
                raw = value.strip()
                if raw.startswith('"'):
                    raw = raw[1:].split('"', 1)[0]
                else:
                    raw = raw.split("#", 1)[0].strip()
                result[key.strip()] = raw
    return result


def notes() -> dict[str, str]:
    result = {}
    if not STATS_NOTES_FILE.exists():
        return result
    heading = None
    body = []
    in_comment = False
    for line in STATS_NOTES_FILE.read_text(encoding=TEXT_ENCODING).splitlines():
        if "<!--" in line:
            in_comment = True
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        metric_heading = re.match(r"^#{1,6}\s+(.+?)\s+\(([a-z][a-z0-9_]*)\)(?:\s+#web)?\s*$", line)
        if metric_heading:
            if heading:
                result[heading] = " ".join(body).strip()
            heading = metric_heading.group(1)
            heading, body = heading, []
        elif line.startswith("#"):
            if heading:
                result[heading] = " ".join(body).strip()
            heading, body = None, []
        elif heading and not line.startswith("<!--"):
            if line.strip(): body.append(line.strip())
    if heading:
        result[heading] = " ".join(body).strip()
    result.setdefault("Couverture stylistique", "Surface sur le graphique radar.")
    return result


def notes_by_id() -> tuple[dict[str, str], dict[str, str], list[str], dict[str, str]]:
    """Retourne notes, titres, ordre et intertitres issus du Markdown."""
    notes, titles, order, sections = {}, {}, [], {}
    heading = body = identifier = None
    blocks = []
    current_section = None
    def flush_body():
        nonlocal body, blocks
        if body:
            blocks.append(" ".join(body).strip())
            body = []
    def save_note():
        nonlocal blocks
        flush_body()
        if identifier is not None:
            notes[str(identifier)] = "\n\n".join(blocks).strip()
        blocks = []
    window_label = f"{ANALYSIS_WINDOW_WORDS:,} mots".replace(",", " ")
    for line in STATS_NOTES_FILE.read_text(encoding=TEXT_ENCODING).replace("{windows}", window_label).splitlines():
        stripped = line.strip()
        match = re.match(r"^#{1,6}\s+(.+?)\s+\(([a-z][a-z0-9_]*)\)(?:\s+#web)?\s*$", stripped)
        if match:
            save_note()
            heading, identifier, body = match.group(1), match.group(2), []
            titles[identifier] = heading
            order.append(identifier)
            if current_section:
                sections[identifier] = current_section
        elif identifier is not None and re.match(r"^#{1,6}\s", stripped):
            save_note()
            heading = body = identifier = None
            section_match = re.match(r"^####\s+(.+?)\s*$", stripped)
            if section_match:
                current_section = section_match.group(1)
            elif re.match(r"^#{1,3}\s", stripped):
                current_section = None
        elif identifier is None:
            section_match = re.match(r"^####\s+(.+?)\s*$", stripped)
            if section_match:
                current_section = section_match.group(1)
            elif re.match(r"^#{1,3}\s", stripped):
                current_section = None
        elif stripped and not line.lstrip().startswith("<!--"):
            body.append(stripped)
        elif identifier is not None and not stripped:
            flush_body()
    save_note()
    return notes, titles, order, sections


def default_radar_ids() -> list[str]:
    """Axes BigFive affichés par défaut, dans l'ordre du tableau principal."""
    return [field for _label, field in BIGFIVE_AXES]


def export_json() -> int:
    WEB_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    note_data, note_titles, metric_order, metric_sections = notes_by_id()
    site = site_config()
    if note_data.get("note_coverage"):
        site["coverage_help"] = note_data["note_coverage"]
    def preferred_label(field: str) -> str:
        title = note_titles.get(field, "")
        return title.split("/", 1)[0].replace("**", "").strip()
    metric_labels = {field: preferred_label(field) for field in METRICS}
    radar_ids = default_radar_ids()
    composite_weights = {
        "classicism_score": CLASSICISM_WEIGHTS,
        "baroque_score": ORNATENESS_WEIGHTS,
        "narrativity_score": NARRATIVITY_WEIGHTS,
        "emotionality_score": EMOTIONALITY_WEIGHTS,
        "discursivite_score": DISCURSIVITE_WEIGHTS,
    }
    if not EPUB_DATABASE.exists():
        payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "site": site, "palette": chart_palette(), "notes": note_data, "note_titles": note_titles, "metric_labels": metric_labels, "metric_order": metric_order, "metric_sections": metric_sections, "default_radar": radar_ids, "raw_metrics": list(RAW_METRICS), "composite_weights": composite_weights, "corpora": [], "books": []}
    else:
        with sqlite3.connect(EPUB_DATABASE) as db:
            db.row_factory = sqlite3.Row
            corpora = [dict(row) for row in db.execute("SELECT id,label FROM corpora ORDER BY id COLLATE NOCASE")]
            books = []
            for book in db.execute("SELECT id,path,title,author,publisher,publication_date,size,sha256 FROM books ORDER BY title COLLATE NOCASE"):
                analyses = []
                for row in db.execute("SELECT window_index,char_start,char_end,char_count FROM analyses WHERE book_id=? ORDER BY window_index", (book["id"],)):
                    stats_data = cached_metric_values(db, book["id"], row["window_index"])
                    for composite_field in composite_weights:
                        stats_data.pop(composite_field, None)
                    required = ("punctuation_ratio", "punctuation_diversity", "structural_diversity", "structural_rhythm", "sentence_start_diversity", "burstiness", "noun_verb_ratio")
                    missing = [field for field in required if field not in stats_data or not isinstance(stats_data[field], (int, float)) or not math.isfinite(stats_data[field])]
                    if missing:
                        raise ValueError(f"Mesures radar absentes pour {book['title']}: {', '.join(missing)}")
                    stats_data.setdefault("document_char_count", book["size"])
                    analyses.append({
                        "window": row["window_index"], "start": row["char_start"], "end": row["char_end"],
                        "chars": row["char_count"], "stats": stats_data,
                    })
                books.append({
                    "id": book["id"], "filename": Path(book["path"]).name, "title": book["title"],
                    "author": book["author"], "publisher": book["publisher"],
                    "publication_date": book["publication_date"], "size": book["size"],
                    "sha256": book["sha256"],
                    "corpora": [row[0] for row in db.execute("SELECT corpus_id FROM corpus_books WHERE book_id=? ORDER BY corpus_id", (book["id"],))],
                    "analyses": analyses,
                })
        payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "site": site, "palette": chart_palette(), "notes": note_data, "note_titles": note_titles, "metric_labels": metric_labels, "metric_order": metric_order, "metric_sections": metric_sections, "default_radar": radar_ids, "raw_metrics": list(RAW_METRICS), "composite_weights": composite_weights, "corpora": corpora, "books": books}
    WEB_DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding=TEXT_ENCODING)
    return len(payload["books"])


if __name__ == "__main__":
    print(f"{export_json()} livres exportés vers {WEB_DATA_FILE}")
