"""Exporte la base SQLite vers les données statiques du site web."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sqlite3

from .config import (BIGFIVE_AXES, EPUB_DATABASE, METRICS, RAW_METRICS,
                     PROMPT_MIN_RATIO, PROMPT_RARE_RATIO, SITE_CONFIG_FILE, TEXT_ENCODING, WEB_DATA_FILE,
                     PROJECT_ROOT,
                     CLASSICISM_WEIGHTS, ORNATENESS_WEIGHTS,
                     NARRATIVITY_WEIGHTS, EMOTIONALITY_WEIGHTS,
                     DISCURSIVITE_WEIGHTS)
from .config import CHART_PALETTE_FILE, STATS_NOTES_FILE
from .metrics import cached_metric_values


def site_config() -> dict[str, str]:
    values = {"name": "Site Unshiter", "author": "Thierry Crouzet", "author_url": "https://tcrouzet.com", "description": "", "copyright": "© {author} — (date) — {livres} livres", "prompt_rewriting": "", "prompt_writing": "", "prompt_ids": "false"}
    if SITE_CONFIG_FILE.exists():
        for line in SITE_CONFIG_FILE.read_text(encoding=TEXT_ENCODING).splitlines():
            key, separator, value = line.partition(":")
            if separator and key.strip() in values:
                values[key.strip()] = value.strip().strip('"\'')
    for key in ("prompt_rewriting", "prompt_writing"):
        if not values[key]:
            continue
        prompt_path = Path(values[key])
        if not prompt_path.is_absolute():
            prompt_path = PROJECT_ROOT / prompt_path
        if not prompt_path.is_file():
            raise FileNotFoundError(f"Prompt introuvable : {prompt_path}")
        values[key] = prompt_path.read_text(encoding=TEXT_ENCODING).strip()
        if "[PLACEHOLDER]" not in values[key]:
            raise ValueError(f"Placeholder [PLACEHOLDER] absent de {prompt_path}")
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
        metric_heading = re.match(r"^#{1,6}\s+(.+?)\s+\(([a-z][a-z0-9_]*)\)(?:\s+#[a-z0-9_-]+)*\s*$", line)
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


def notes_by_id() -> tuple[dict[str, str], dict[str, str], list[str], dict[str, str], dict[str, set[str]], dict[str, str]]:
    """Retourne notes, titres, ordre et intertitres issus du Markdown."""
    notes, titles, order, sections, tags, quotes = {}, {}, [], {}, {}, {}
    heading = body = identifier = None
    quote_lines = []
    blocks = []
    current_section = None
    def flush_body():
        nonlocal body, blocks
        if body:
            blocks.append(" ".join(body).strip())
            body = []
    def save_note():
        nonlocal blocks, quote_lines
        flush_body()
        if identifier is not None:
            notes[str(identifier)] = "\n\n".join(blocks).strip()
            if quote_lines:
                quotes[str(identifier)] = " ".join(quote_lines)
        blocks = []
        quote_lines = []
    for line in STATS_NOTES_FILE.read_text(encoding=TEXT_ENCODING).splitlines():
        stripped = line.strip()
        match = re.match(r"^#{1,6}\s+(.+?)\s+\(([a-z][a-z0-9_]*)\)(?P<tags>(?:\s+#[a-z0-9_-]+)*)\s*$", stripped)
        if match:
            save_note()
            heading, identifier, body = match.group(1), match.group(2), []
            titles[identifier] = heading
            tags[identifier] = set(re.findall(r"#([a-z0-9_-]+)", match.group("tags")))
            if identifier in order:
                order.remove(identifier)
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
            if stripped.startswith(">"):
                quote_lines.append(stripped[1:].strip())
        elif identifier is not None and not stripped:
            flush_body()
    save_note()
    return notes, titles, order, sections, tags, quotes


def default_radar_ids() -> list[str]:
    """Axes BigFive affichés par défaut, dans l'ordre du tableau principal."""
    return [field for _label, field in BIGFIVE_AXES]


def missing_export_fields(stats: dict[str, object], excluded: set[str]) -> list[str]:
    return [
        field for field in METRICS
        if field not in excluded
        and (field not in stats or not isinstance(stats[field], (int, float)) or not math.isfinite(stats[field]))
    ]


def ensure_nonempty_export(indexed_books: int, exported_books: list[dict]) -> None:
    if indexed_books and not exported_books:
        raise ValueError("Aucune œuvre complète à exporter ; web/data.json existant conservé")


def export_json() -> int:
    WEB_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    note_data, note_titles, metric_order, metric_sections, metric_tags, metric_quotes = notes_by_id()
    exported_metric_tags = {field: sorted(tags) for field, tags in metric_tags.items()}
    site = site_config()
    if note_data.get("note_coverage"):
        site["coverage_help"] = note_data["note_coverage"]
    def preferred_label(field: str) -> str:
        title = note_titles.get(field, "")
        return title.split("/", 1)[0].replace("**", "").strip()
    metric_labels = {field: preferred_label(field) for field in METRICS}
    metrics = [
        {
            "id": field,
            "label": metric_labels[field],
            "title": note_titles.get(field, ""),
            "note": note_data.get(field, ""),
            "section": metric_sections.get(field, ""),
            "tags": sorted(metric_tags.get(field, set())),
        }
        for field in METRICS
    ]
    radar_ids = default_radar_ids()
    composite_weights = {
        "classicism_score": CLASSICISM_WEIGHTS,
        "baroque_score": ORNATENESS_WEIGHTS,
        "narrativity_score": NARRATIVITY_WEIGHTS,
        "emotionality_score": EMOTIONALITY_WEIGHTS,
        "discursivite_score": DISCURSIVITE_WEIGHTS,
    }
    if not EPUB_DATABASE.exists():
        payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "site": site, "palette": chart_palette(), "metrics": metrics, "notes": note_data, "note_titles": note_titles, "metric_labels": metric_labels, "metric_order": metric_order, "metric_sections": metric_sections, "metric_tags": exported_metric_tags, "metric_quotes": metric_quotes, "prompt_min_ratio": PROMPT_MIN_RATIO, "prompt_rare_ratio": PROMPT_RARE_RATIO, "default_radar": radar_ids, "raw_metrics": list(RAW_METRICS), "composite_weights": composite_weights, "corpora": [], "books": []}
    else:
        with sqlite3.connect(EPUB_DATABASE) as db:
            db.row_factory = sqlite3.Row
            indexed_books = db.execute("SELECT COUNT(*) FROM books").fetchone()[0]
            corpora = [dict(row) for row in db.execute("SELECT id,label FROM corpora ORDER BY id COLLATE NOCASE")]
            books = []
            for book in db.execute("SELECT id,path,title,author,publisher,publication_date,size,sha256 FROM books ORDER BY title COLLATE NOCASE"):
                analyses = []
                complete = True
                for row in db.execute("SELECT window_index FROM analyses WHERE book_id=? ORDER BY window_index", (book["id"],)):
                    stats_data = cached_metric_values(db, book["id"], row["window_index"])
                    for composite_field in composite_weights:
                        stats_data.pop(composite_field, None)
                    if missing_export_fields(stats_data, set(composite_weights)):
                        complete = False
                        break
                    stats_data.setdefault("document_char_count", book["size"])
                    analyses.append({
                        "window": row["window_index"], "start": 0, "end": book["size"],
                        "chars": book["size"], "stats": stats_data,
                    })
                if not complete or not analyses:
                    continue
                books.append({
                    "id": book["id"], "filename": Path(book["path"]).name, "title": book["title"],
                    "author": book["author"], "publisher": book["publisher"],
                    "publication_date": book["publication_date"], "size": book["size"],
                    "sha256": book["sha256"],
                    "corpora": [row[0] for row in db.execute("SELECT corpus_id FROM corpus_books WHERE book_id=? ORDER BY corpus_id", (book["id"],))],
                    "analyses": analyses,
                })
            exported_corpora = {corpus for book in books for corpus in book["corpora"]}
            corpora = [corpus for corpus in corpora if corpus["id"] in exported_corpora]
            ensure_nonempty_export(indexed_books, books)
        payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "site": site, "palette": chart_palette(), "metrics": metrics, "notes": note_data, "note_titles": note_titles, "metric_labels": metric_labels, "metric_order": metric_order, "metric_sections": metric_sections, "metric_tags": exported_metric_tags, "metric_quotes": metric_quotes, "prompt_min_ratio": PROMPT_MIN_RATIO, "prompt_rare_ratio": PROMPT_RARE_RATIO, "default_radar": radar_ids, "raw_metrics": list(RAW_METRICS), "composite_weights": composite_weights, "corpora": corpora, "books": books}
    WEB_DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding=TEXT_ENCODING)
    return len(payload["books"])


if __name__ == "__main__":
    print(f"{export_json()} livres exportés vers {WEB_DATA_FILE}")
