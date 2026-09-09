"""Utilitaires communs liés au registre des mesures."""

import re
import json
import math

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
    repetition_word_count = values.get("repetition_word_count") or 0
    for count_field, ratio_field in (
        ("global_repetition_count", "global_repetition_ratio"),
        ("local_repetition_count", "local_repetition_ratio"),
        ("global_phonetic_repetition_count", "global_phonetic_repetition_ratio"),
        ("local_phonetic_repetition_count", "local_phonetic_repetition_ratio"),
        ("absolute_repetition_count", "absolute_repetition_rate"),
    ):
        if count_field in values:
            values[ratio_field] = values[count_field] / repetition_word_count if repetition_word_count else 0
    if word_count:
        if "unique_lemma_count" in values:
            values["lemma_diversity_ratio"] = values["unique_lemma_count"] / word_count
        if "distinct_form_count" in values:
            values["type_token_ratio"] = values["distinct_form_count"] / word_count
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
        if "logical_connector_count" in values:
            values["logical_connector_ratio"] = values["logical_connector_count"] / sentence_count * 100
    common_noun_count = values.get("common_noun_count") or 0
    if common_noun_count and "abstract_noun_count" in values:
        values["abstract_noun_ratio"] = values["abstract_noun_count"] / common_noun_count
    conjugue_verb_count = values.get("conjugue_verb_count") or 0
    if conjugue_verb_count and "gnomic_present_count" in values:
        values["gnomic_present_ratio"] = values["gnomic_present_count"] / conjugue_verb_count
    verb_count = values.get("verb_count") or 0
    if verb_count and "modal_generalization_count" in values:
        values["modal_generalization_ratio"] = values["modal_generalization_count"] / verb_count
    lexical_word_count = values.get("lexical_word_count") or 0
    if lexical_word_count:
        if "unique_lemma_count" in values:
            values["global_lemma_richness"] = values["unique_lemma_count"] / lexical_word_count
        if "morphalou_recognized_count" in values:
            values["morphalou_coverage"] = values["morphalou_recognized_count"] / lexical_word_count
    unique_lemma_count = values.get("unique_lemma_count") or 0
    if "hapax_count" in values:
        values["hapax_ratio"] = values["hapax_count"] / unique_lemma_count if unique_lemma_count else 0
    if "emotion_word_count" in values:
        values["emotion_word_ratio"] = values["emotion_word_count"] / lexical_word_count if lexical_word_count else 0
    if "sentence_count" in values and "emotion_sentence_count" in values:
        values["emotion_sentence_ratio"] = values["emotion_sentence_count"] / values["sentence_count"] if values["sentence_count"] else 0
    sentence_count = values.get("sentence_count") or 0
    word_count = values.get("word_count") or 0
    narrative_verbs = values.get("narrative_verb_count") or 0
    if sentence_count:
        for ratio, count in {
            "metaphorical_comme_ratio": "methaphore_count",
            "scene_summary_ratio": "summary_sentence_count",
            "negation_ratio": "negative_sentence_count",
            "ellipsis_ratio": "suspention_point_count",
            "exclamation_ratio": "exclamation_point_count",
            "exclamative_construction_ratio": "exclamative_sentence_count",
        }.items():
            if count in values:
                values[ratio] = values[count] / sentence_count
        if "temporal_connector_count" in values:
            values["temporal_connector_ratio"] = values["temporal_connector_count"] / sentence_count * 100
    if word_count:
        for ratio, count in {
            "present_participle_ratio": "present_participe_count",
            "past_participle_ratio": "past_participe_count",
            "dialogue_ratio": "dialog_word_count",
        }.items():
            if count in values:
                values[ratio] = values[count] / word_count
        if "familiarity_marker_count" in values:
            values["oral_familiarity_ratio"] = values["familiarity_marker_count"] / word_count * 100
    if narrative_verbs:
        for ratio, count in {
            "simple_past_ratio": "simple_past_count",
            "literary_subjunctive_ratio": "subjonctive_count",
            "action_verb_ratio": "active_verb_count",
            "narrative_past_ratio": "narrative_past_count",
        }.items():
            if count in values:
                values[ratio] = values[count] / narrative_verbs
    negations = values.get("negation_count") or 0
    if "verb_negation_count" in values:
        values["negation_completeness_ratio"] = values["verb_negation_count"] / negations if negations else 0
    futures = (values.get("va_count") or 0) + (values.get("future_count") or 0)
    if "va_count" in values:
        values["periphrastic_future_ratio"] = values["va_count"] / futures if futures else 0
    subjects = values.get("classifiable_subject_count") or 0
    if "personal_subject_count" in values:
        values["personal_subject_ratio"] = values["personal_subject_count"] / subjects if subjects else 0
    lexical_tokens = values.get("lexical_token_count") or 0
    if "proper_noun_count" in values:
        values["proper_noun_density"] = values["proper_noun_count"] / lexical_tokens if lexical_tokens else 0
    common_nouns = values.get("common_noun_count") or 0
    if "concrate_noun_count" in values:
        values["concrete_noun_ratio"] = values["concrate_noun_count"] / common_nouns if common_nouns else 0
    transitions = values.get("tense_transition_count") or 0
    if "tense_shift_count" in values:
        values["tense_shift_rate"] = values["tense_shift_count"] / transitions if transitions else 0
    adjective_count = values.get("adjective_count") or 0
    if "intensified_adjective_count" in values:
        values["intensifier_adjective_ratio"] = values["intensified_adjective_count"] / adjective_count if adjective_count else 0
    utf8_byte_count = values.get("utf8_byte_count") or 0
    if "gzip_byte_count" in values:
        values["gzip_compression_ratio"] = values["gzip_byte_count"] / utf8_byte_count if utf8_byte_count else 0
    if sentence_count and all(field in values for field in ("semicolons_count", "colon_count", "dash_count")):
        values["punctuation_variety_score"] = (
            values["semicolons_count"] + values["colon_count"] + values["dash_count"]
        ) / sentence_count
    punctuation_counts = [
        values.get(field) for field in (
            "period_count", "comma_count", "semicolons_count", "colon_count",
            "question_mark_count", "exclamation_point_count", "dash_count",
            "parenthesis_count", "quote_mark_count", "suspention_point_count",
        )
    ]
    if all(isinstance(value, (int, float)) for value in punctuation_counts):
        total_punctuation = sum(punctuation_counts)
        # Le compteur global est persiste : c'est le numerateur brut de la
        # densite. La somme garde la lecture des anciennes bases compatible.
        punctuation_mark_count = values.get("punctuation_mark_count", total_punctuation)
        values["punctuation_ratio"] = punctuation_mark_count / word_count if word_count else 0
        values["punctuation_diversity"] = (
            -sum((count / total_punctuation) * math.log2(count / total_punctuation)
                 for count in punctuation_counts if count) / math.log2(len(punctuation_counts))
            if total_punctuation else 0
        )
    grammatical_total = values.get("grammatical_token_count") or 0
    grammatical_nouns = (values.get("common_noun_count") or 0) + (values.get("proper_noun_count") or 0)
    grammatical_verbs = values.get("grammatical_verb_count") or 0
    if grammatical_total:
        values["noun_ratio"] = grammatical_nouns / grammatical_total
        values["verb_ratio"] = grammatical_verbs / grammatical_total
        values["adjective_ratio"] = (values.get("adjective_count") or 0) / grammatical_total
        values["adverb_ratio"] = (values.get("adverb_count") or 0) / grammatical_total
    # Les corpus anciens peuvent encore posséder le ratio validé sans son
    # nouveau dénominateur brut. Ne jamais écraser cette valeur par zéro : le
    # ratio sera reconstruit dès que grammatical_verb_count aura été calculé.
    if "grammatical_verb_count" in values:
        values["noun_verb_ratio"] = grammatical_nouns / grammatical_verbs if grammatical_verbs else 0
    if "function_word_count" in values:
        values["function_word_ratio"] = values["function_word_count"] / word_count if word_count else 0
    if sentence_count:
        if "active_sentence_count" in values:
            values["active_voice_ratio"] = values["active_sentence_count"] / sentence_count
        if "adjective_chain_count" in values:
            values["adjective_chain_ratio"] = values["adjective_chain_count"] / sentence_count
        if "incise_count" in values:
            values["incise_density"] = values["incise_count"] / sentence_count
        if "coordination_accumulation_count" in values:
            values["coordination_accumulation_ratio"] = values["coordination_accumulation_count"] / sentence_count
    analyzed_nouns = values.get("analyzed_noun_count") or 0
    if "noun_modifier_count" in values:
        values["avg_modifiers_per_noun"] = values["noun_modifier_count"] / analyzed_nouns if analyzed_nouns else 0
    if "heavily_modified_noun_count" in values:
        values["heavily_modified_noun_ratio"] = values["heavily_modified_noun_count"] / analyzed_nouns if analyzed_nouns else 0
    chains = values.get("adjective_chain_count") or 0
    if "adjective_in_chain_count" in values:
        values["avg_adjective_chain_length"] = values["adjective_in_chain_count"] / chains if chains else 0
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
