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
    word_count = values.get("word_count") or 0
    if word_count:
        if "common_noun_count" in values:
            values["common_noun_ratio"] = values["common_noun_count"] / word_count
        if "proper_noun_count" in values:
            values["proper_noun_ratio"] = values["proper_noun_count"] / word_count
    sentence_count = values.get("sentence_count") or 0
    if sentence_count:
        for count_field, ratio_field in (
            ("nominal_sentence_count", "nominal_sentence_ratio"),
            ("relative_clause_count", "relative_clause_ratio"),
            ("subordinate_clause_count", "subordinate_clause_ratio"),
        ):
            if count_field in values:
                values[ratio_field] = values[count_field] / sentence_count
        if "question_mark_count" in values:
            values["question_mark_ratio"] = values["question_mark_count"] / sentence_count
    if "lemma_count" in values:
        values["lexical_word_count"] = values["lemma_count"]
    emotion_categories = (
        "joy", "sadness", "fear", "anger", "surprise", "disgust", "contempt", "somatic",
    )
    emotion_counts = [values.get(f"{category}_emotion_count") for category in emotion_categories]
    intensified_counts = [values.get(f"{category}_intensified_emotion_count") for category in emotion_categories]
    if all(isinstance(value, (int, float)) for value in emotion_counts + intensified_counts):
        emotional_total = sum(emotion_counts)
        values["emotion_intensification_ratio"] = sum(intensified_counts) / emotional_total if emotional_total else 0
    return values


def windowed_metric_fields() -> set[str]:
    """Champs dont la note demande explicitement le calcul par fenêtre."""
    if not STATS_NOTES_FILE.exists():
        return set()
    fields: set[str] = set()
    current_field = None
    for line in STATS_NOTES_FILE.read_text(encoding=TEXT_ENCODING).splitlines():
        heading = re.match(r"^#{1,6} .* \(([a-z][a-z0-9_]*)\)\s*$", line.strip())
        if heading:
            current_field = heading.group(1)
        elif current_field and "{windows}" in line:
            fields.add(current_field)
    return fields.intersection(METRICS)
