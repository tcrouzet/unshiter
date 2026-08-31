"""Exporte la base SQLite vers les données statiques du site web."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sqlite3

from .config import (BIGFIVE_AXES, EPUB_ANALYSIS_WINDOW_SIZE, EPUB_DATABASE, METRICS,
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
        metric_heading = re.match(r"^#{1,6}\s+(.+?)\s+\(([a-z][a-z0-9_]*)\)\s*$", line)
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


def notes_by_id() -> tuple[dict[str, str], dict[str, str]]:
    """Retourne les notes et titres indexés par leur fonction."""
    notes, titles = {}, {}
    heading = body = identifier = None
    blocks = []
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
    window_label = f"{EPUB_ANALYSIS_WINDOW_SIZE / 1000:g}"
    for line in STATS_NOTES_FILE.read_text(encoding=TEXT_ENCODING).replace("{windows}", window_label).splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s+\(([a-z][a-z0-9_]*)\)\s*$", line.strip())
        if match:
            save_note()
            heading, identifier, body = match.group(1), match.group(2), []
            titles[identifier] = heading
        elif identifier is not None and re.match(r"^#{1,6}\s", line.strip()):
            save_note()
            heading = body = identifier = None
        elif identifier is not None and line.strip() and not line.lstrip().startswith("<!--"):
            body.append(line.strip())
        elif identifier is not None and not line.strip():
            flush_body()
    save_note()
    return notes, titles


def default_radar_ids() -> list[str]:
    """Axes BigFive affichés par défaut, dans l'ordre du tableau principal."""
    return [field for _label, field in BIGFIVE_AXES]


def export_json() -> int:
    WEB_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    note_data, note_titles = notes_by_id()
    site = site_config()
    if note_data.get("note_coverage"):
        site["coverage_help"] = note_data["note_coverage"]
    def preferred_label(field: str) -> str:
        title = note_titles.get(field, "")
        bold = re.findall(r"\*\*([^*]+)\*\*", title)
        return bold[0].strip() if bold else title.split("/")[0].strip()
    metric_labels = {field: preferred_label(field) for field in METRICS}
    radar_ids = default_radar_ids()
    if not EPUB_DATABASE.exists():
        payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "site": site, "palette": chart_palette(), "notes": note_data, "note_titles": note_titles, "metric_labels": metric_labels, "default_radar": radar_ids, "books": []}
    else:
        with sqlite3.connect(EPUB_DATABASE) as db:
            db.row_factory = sqlite3.Row
            books = []
            for book in db.execute("SELECT id,path,title,author,publisher,publication_date,size,sha256 FROM books ORDER BY title COLLATE NOCASE"):
                analyses = []
                for row in db.execute("SELECT window_index,char_start,char_end,char_count FROM analyses WHERE book_id=? ORDER BY window_index", (book["id"],)):
                    stats_data = cached_metric_values(db, book["id"], row["window_index"])
                    required = ("punctuation_per_300_words", "punctuation_diversity", "structural_diversity", "structural_rhythm", "sentence_start_diversity", "burstiness", "noun_verb_ratio", "filtered_repetition_rate")
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
                    "sha256": book["sha256"], "analyses": analyses,
                })
            # Même échelle pour tout le corpus : l’œuvre au score brut maximal
            # devient la référence 100 % dans l’interface.
            # Normalisation des composantes brutes avant pondération. Les
            # scores composites ne sont jamais normalisés après coup.
            def component(field, analysis, maxima):
                value = analysis["stats"].get(field, 0)
                if not isinstance(value, (int, float)):
                    return 0.0
                maximum = maxima.get(field, 0)
                return value / maximum if maximum else 0.0

            component_weights = {
                "classicism_score": CLASSICISM_WEIGHTS,
                "baroque_score": ORNATENESS_WEIGHTS,
                "narrativity_score": NARRATIVITY_WEIGHTS,
                "emotionality_score": EMOTIONALITY_WEIGHTS,
                "discursivite_score": DISCURSIVITE_WEIGHTS,
            }
            component_fields = {axis: tuple(weights) for axis, weights in component_weights.items()}
            maxima = {}
            for fields_for_axis in component_fields.values():
                for field in fields_for_axis:
                    values = [a["stats"].get(field) for b in books for a in b["analyses"] if isinstance(a["stats"].get(field), (int, float))]
                    maxima[field] = max(values, default=0)
            for book in books:
                for analysis in book["analyses"]:
                    c = lambda field: component(field, analysis, maxima)
                    # Chaque composante est d'abord divisée par son maximum
                    # observé dans tout le corpus. Les poids de config.py sont
                    # ensuite appliqués ; aucun composite brut n'est pondéré.
                    weighted = lambda weights: sum(weight * c(field) for field, weight in weights.items())
                    values = {
                        "classicism_score": weighted(CLASSICISM_WEIGHTS),
                        "baroque_score": weighted(ORNATENESS_WEIGHTS),
                        "narrativity_score": weighted(NARRATIVITY_WEIGHTS),
                        "emotionality_score": weighted(EMOTIONALITY_WEIGHTS),
                        "discursivite_score": weighted(DISCURSIVITE_WEIGHTS),
                    }
                    for field, value in values.items():
                        analysis["stats"][field] = value
        payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "site": site, "palette": chart_palette(), "notes": note_data, "note_titles": note_titles, "metric_labels": metric_labels, "default_radar": radar_ids, "books": books}
    WEB_DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding=TEXT_ENCODING)
    return len(payload["books"])


if __name__ == "__main__":
    print(f"{export_json()} livres exportés vers {WEB_DATA_FILE}")
