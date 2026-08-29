"""Utilitaires communs liés au registre des mesures."""

import re
import json

from .config import METRICS, STATS_NOTES_FILE, TEXT_ENCODING


def cached_metric_values(connection, book_id: int, window_index: int = 0) -> dict:
    """Lit les valeurs d'une analyse depuis le cache SQLite par mesure."""
    rows = connection.execute(
        "SELECT metric_name, value_json FROM metric_cache "
        "WHERE book_id = ? AND window_index = ?",
        (book_id, window_index),
    ).fetchall()
    values = {}
    for metric_name, value_json in rows:
        try:
            values[metric_name] = json.loads(value_json)
        except (TypeError, json.JSONDecodeError):
            continue
    return values


def windowed_metric_fields() -> set[str]:
    """Champs dont la note demande explicitement le calcul par fenêtre."""
    if not STATS_NOTES_FILE.exists():
        return set()
    fields: set[str] = set()
    current_field = None
    for line in STATS_NOTES_FILE.read_text(encoding=TEXT_ENCODING).splitlines():
        heading = re.match(r"^# .* \(([a-z][a-z0-9_]*)\)\s*$", line.strip())
        if heading:
            current_field = heading.group(1)
        elif current_field and "{windows}" in line:
            fields.add(current_field)
    return fields.intersection(METRICS)
