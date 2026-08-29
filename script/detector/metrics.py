"""Utilitaires communs liés au registre des mesures."""

import re
import json

from .config import FIELD_BY_METRIC_ID, STATS_NOTES_FILE, TEXT_ENCODING


def cached_metric_values(connection, book_id: int, window_index: int = 0) -> dict:
    """Lit les valeurs d'une analyse depuis le cache SQLite par mesure."""
    rows = connection.execute(
        "SELECT metric_id, value_json FROM metric_cache "
        "WHERE book_id = ? AND window_index = ?",
        (book_id, window_index),
    ).fetchall()
    values = {}
    for metric_id, value_json in rows:
        try:
            values[metric_id] = json.loads(value_json)
        except (TypeError, json.JSONDecodeError):
            continue
    return values


def windowed_metric_fields() -> set[str]:
    """Champs dont la note demande explicitement le calcul par fenêtre."""
    if not STATS_NOTES_FILE.exists():
        return set()
    note_ids: set[str] = set()
    current_id = None
    for line in STATS_NOTES_FILE.read_text(encoding=TEXT_ENCODING).splitlines():
        heading = re.match(r"^# .*?#(\d+)\s*$", line.strip())
        if heading:
            current_id = f"mesure_{heading.group(1)}"
        elif current_id and "{windows}" in line:
            note_ids.add(current_id)
    return {
        FIELD_BY_METRIC_ID[identifier]
        for identifier in note_ids
        if identifier in FIELD_BY_METRIC_ID
    }
