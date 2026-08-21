"""Exporte la base SQLite vers les données statiques du site web."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sqlite3

from .config import EPUB_ANALYSIS_WINDOW_SIZE, EPUB_DATABASE, METRIC_ID_BY_FIELD, SITE_CONFIG_FILE, TEXT_ENCODING, WEB_DATA_FILE
from .config import CHART_PALETTE_FILE, STATS_NOTES_FILE


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
        if line.startswith("# "):
            if heading:
                result[heading] = " ".join(body).strip()
            heading = re.sub(r"\s+#\d+\s*$", "", line[2:].strip())
            heading, body = heading, []
        elif heading and not line.startswith("<!--"):
            if line.strip(): body.append(line.strip())
    if heading:
        result[heading] = " ".join(body).strip()
    result.setdefault("Couverture stylistique", "Surface sur le graphique radar.")
    return result


def note_ids() -> dict[str, str]:
    """Associe les clés techniques aux titres portant un identifiant #N."""
    if not STATS_NOTES_FILE.exists():
        return {}
    result = {}
    titles = {
        "Densité de ponctuations / Sparsité de ponctuations": "punctuation_per_300_words",
        "Diversité de ponctuation": "punctuation_diversity", "Diversité des structures": "structural_diversity",
        "Rythme des structures": "structural_rhythm", "Diversité des débuts de phrase": "sentence_start_diversity",
        "Burstiness": "burstiness", "Ratio noms/verbes": "noun_verb_ratio", "Répétitions lexicales": "filtered_repetition_rate",
        "Diversité stylistique": "stylistic_repetition_rate", "Répétitions familiales": "family_repetition_rate",
        "Répétitions sonores": "phonetic_repetition_rate", "Répétitions non filtrées": "absolute_repetition_rate",
        "Mots-outils": "function_word_ratio", "Répétition globale des trigrammes": "trigram_repetition",
        "Répétition locale des trigrammes": "moving_trigram_repetition", "Noms": "noun_ratio", "Verbes": "verb_ratio",
        "Adjectifs": "adjective_ratio", "Adverbes": "adverb_ratio", "Diversité de longueurs de phrase (mots)": "sentence_word_std_dev",
        "Compression gzip": "gzip_compression_ratio", "Relatives et subordonnées": "relative_clause_ratio",
        "Phrases nominales": "nominal_sentence_ratio", "Voix active": "active_voice_ratio",
        "Comparaisons métaphoriques": "metaphorical_comme_ratio", "Profondeur syntaxique": "average_syntactic_depth",
        "Formes par lemme": "form_lemma_ratio", "Mots employés une seule fois": "hapax_ratio",
    }
    for line in STATS_NOTES_FILE.read_text(encoding=TEXT_ENCODING).splitlines():
        stripped = line.strip()
        match = re.match(r"^# (.+?)\s+#(\d+)\s*$", stripped)
        if not match:
            continue
        title, identifier = match.group(1), int(match.group(2))
        if title in titles:
            result[titles[title]] = identifier
    return result


def metric_note_ids() -> dict[str, str]:
    """Correspondance unique définie dans config.py, jamais par un libellé."""
    return dict(METRIC_ID_BY_FIELD)
    """legacy mapping removed"""
    keys = [
        "punctuation_per_300_words", "punctuation_diversity", "structural_diversity", "structural_rhythm",
        "sentence_start_diversity", "burstiness", "noun_verb_ratio", "filtered_repetition_rate",
        "stylistic_repetition_rate", "family_repetition_rate", "phonetic_repetition_rate", "absolute_repetition_rate",
        "function_word_ratio", "trigram_repetition", "moving_trigram_repetition", "noun_ratio", "verb_ratio",
        "adjective_ratio", "adverb_ratio", "gzip_compression_ratio", "relative_clause_ratio",
        "nominal_sentence_ratio", "active_voice_ratio", "metaphorical_comme_ratio", "average_syntactic_depth",
        "form_lemma_ratio", "hapax_ratio",
        "word_count", "sentence_count", "paragraph_count", "avg_word_length", "avg_sentence_length",
        "avg_sentence_word_count", "median_sentence_length", "sentence_length_p10", "sentence_length_p90",
        "paragraph_length_std_dev",
        "document_char_count",
    ]
    return {key: f"mesure_{index}" for index, key in enumerate(keys[:27], 1)} | {"hapax_ratio": "mesure_28"} | {key: f"mesure_{index}" for index, key in enumerate(keys[27:], 30)}


def notes_by_id() -> tuple[dict[str, str], dict[str, str]]:
    """Retourne les notes et leurs titres, indexés exclusivement par #N."""
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
        match = re.match(r"^# (.+?)\s+#(\d+)(?:\s+#tab1_\d+)?\s*$", line.strip())
        if match:
            save_note()
            heading, identifier, body = match.group(1), int(match.group(2)), []
            titles[str(identifier)] = heading
        elif identifier is not None and line.strip() and not line.lstrip().startswith("<!--"):
            body.append(line.strip())
        elif identifier is not None and not line.strip():
            flush_body()
    save_note()
    return notes, titles


def default_radar_ids() -> list[str]:
    """Lit l’ordre #tab1_N directement dans stats-notes.md."""
    by_note = {identifier.split("_")[-1]: identifier for identifier in METRIC_ID_BY_FIELD.values()}
    found = []
    for line in STATS_NOTES_FILE.read_text(encoding=TEXT_ENCODING).splitlines():
        match = re.match(r"^# .+? #(\d+) #tab1_(\d+)\s*$", line.strip())
        if match and match.group(1) in by_note:
            found.append((int(match.group(2)), by_note[match.group(1)]))
    return [identifier for _, identifier in sorted(found)]


def export_json() -> int:
    WEB_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    note_data, note_titles = notes_by_id()
    site = site_config()
    if note_data.get("29"):
        site["coverage_help"] = note_data["29"]
    public_note_ids = {f"mesure_{identifier}": identifier for identifier in sorted(int(key) for key in note_data)}
    metric_note_map = metric_note_ids()
    def preferred_label(public_id: str) -> str:
        title = note_titles.get(str(int(public_id.split("_")[-1])), "")
        bold = re.findall(r"\*\*([^*]+)\*\*", title)
        return bold[0].strip() if bold else title.split("/")[0].strip()
    metric_labels = {key: preferred_label(public_id) for key, public_id in metric_note_map.items()}
    radar_ids = default_radar_ids()
    if not EPUB_DATABASE.exists():
        payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "site": site, "palette": chart_palette(), "notes": note_data, "note_titles": note_titles, "metric_note_ids": metric_note_map, "metric_labels": metric_labels, "note_ids": public_note_ids, "default_radar": radar_ids, "books": []}
    else:
        with sqlite3.connect(EPUB_DATABASE) as db:
            db.row_factory = sqlite3.Row
            books = []
            for book in db.execute("SELECT id,path,title,author,publisher,publication_date,size,sha256 FROM books ORDER BY title COLLATE NOCASE"):
                analyses = []
                for row in db.execute("SELECT window_index,char_start,char_end,char_count,stats_json FROM analyses WHERE book_id=? ORDER BY window_index", (book["id"],)):
                    stats_data = json.loads(row["stats_json"])
                    required = ("punctuation_per_300_words", "punctuation_diversity", "structural_diversity", "structural_rhythm", "sentence_start_diversity", "burstiness", "noun_verb_ratio", "filtered_repetition_rate")
                    missing = [field for field in required if METRIC_ID_BY_FIELD[field] not in stats_data or not isinstance(stats_data[METRIC_ID_BY_FIELD[field]], (int, float)) or not math.isfinite(stats_data[METRIC_ID_BY_FIELD[field]])]
                    if missing:
                        raise ValueError(f"Mesures radar absentes pour {book['title']}: {', '.join(missing)}")
                    stats_data.setdefault(METRIC_ID_BY_FIELD["document_char_count"], book["size"])
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
        payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "site": site, "palette": chart_palette(), "notes": note_data, "note_titles": note_titles, "metric_note_ids": metric_note_map, "metric_labels": metric_labels, "note_ids": public_note_ids, "default_radar": radar_ids, "books": books}
    WEB_DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding=TEXT_ENCODING)
    return len(payload["books"])


if __name__ == "__main__":
    print(f"{export_json()} livres exportés vers {WEB_DATA_FILE}")
