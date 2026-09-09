"""Port Python des métriques de stats.js, adaptées au français."""

from collections import Counter
from functools import cached_property, lru_cache
import gzip
import math
import re

from .config import (ORNATENESS_WEIGHTS, CLASSICISM_WEIGHTS, NARRATIVITY_WEIGHTS, EMOTIONALITY_WEIGHTS, DISCURSIVITE_WEIGHTS, STATIVE_VERBS_FILE, TEMPORAL_CONNECTORS_FILE, LOGICAL_CONNECTORS_FILE, FAMILIARITY_MARKERS_FILE, EMOTIONS_FILE,
    FUNCTION_WORDS_FILE, DURATION_MARKERS_FILE, PHONETIC_MIN_RATIO, ANALYSIS_WINDOW_WORDS,
    PHONETIC_MIN_SEQUENCE, TEXT_ENCODING, METRICS)
from .demonette import family_lexemes, family_map, phonetic_map
from .morphalou import contextual_lemma_map, lemma_map, lexical_map
from .syntax_depth import _pipeline, analyze_contextual_tokens, analyze_syntax, dialogue_char_ranges, right_branching_depth as _right_branching_depth
from .lexical_frequency import frequency_map


def normalize_markdown_text(text: str) -> str:
    """Normalise la typographie commune avant toute analyse d'un Markdown."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\.{3,}", "…", text)
    return re.sub(r"\n(?:[ \t]*\n){2,}", "\n\n", text)


def _std(values) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def _load_function_words() -> tuple[set[str], set[str], set[str], set[str]]:
    """Charge les mots et catégories depuis assets/dictionnaires/function-words.txt."""
    words, categories, lemmas, kept_words = set(), set(), set(), set()
    for raw_line in FUNCTION_WORDS_FILE.read_text(encoding=TEXT_ENCODING).splitlines():
        line = raw_line.strip().lower()
        if not line or line.startswith("#"):
            continue
        kind, separator, value = line.partition(":")
        if not separator or not value.strip():
            raise ValueError(f"Entrée invalide dans {FUNCTION_WORDS_FILE}: {raw_line!r}")
        if kind == "mot":
            words.add(value.strip().replace("’", "'"))
        elif kind == "garder":
            kept_words.add(value.strip().replace("’", "'"))
        elif kind == "lemme":
            lemmas.add(value.strip().replace("’", "'"))
        elif kind == "catégorie":
            categories.add(value.strip())
        elif kind in {"familier", "famille", "position"}:
            # Anciennes entrées conservées pour compatibilité avec le fichier
            # historique ; les nouveaux marqueurs sont dans leur fichier dédié.
            words.add(value.strip().replace("’", "'"))
        else:
            raise ValueError(f"Type inconnu dans {FUNCTION_WORDS_FILE}: {kind!r}")
    return words, categories, lemmas, kept_words


class Metrics:
    """Contexte et fonctions de mesure d'un même texte.

    Les propriétés sont paresseuses : la tokenisation et le pipeline spaCy ne
    sont exécutés qu'au moment où une mesure les demande, puis leur résultat
    est réutilisé par les mesures suivantes.
    """

    def __init__(self, text: str, progress=None, shared_metrics=None):
        self.text = text
        self.progress = progress
        self.shared_metrics = shared_metrics or {}

    @cached_property
    def tokens(self):
        return tokenize(self.text)

    @property
    def words(self):
        return self.tokens

    @cached_property
    def sentences(self):
        return split_sentences(self.text)

    @cached_property
    def paragraphs(self):
        return [part for part in re.split(r"\n\s*\n", self.text) if part.strip()]

    @cached_property
    def doc(self):
        pipeline = _pipeline()
        if pipeline is None:
            return None
        if len(self.text) > pipeline.max_length:
            pipeline.max_length = len(self.text) + 1
        return pipeline(self.text)

    @cached_property
    def syntax(self):
        return analyze_syntax(self.text, self.doc)

    @cached_property
    def contextual_tokens(self):
        return analyze_contextual_tokens(self.text, self.doc)

    @cached_property
    def repetition_words(self):
        if self.contextual_tokens is not None:
            return [token for token in self.contextual_tokens if len(token[0]) >= 2]
        return [word for word in tokenize(self.text.replace("’", " ").replace("'", " ")) if len(word) >= 2]

    @cached_property
    def trigram_lemma_values(self):
        return _trigram_lemmas(self.words, self.repetition_words)

    @cached_property
    def dialogue_ranges(self):
        return dialogue_char_ranges(self.text)

    @cached_property
    def pos_counts(self):
        """Comptes grammaticaux bruts issus de l'unique analyse spaCy."""
        if self.doc is None:
            return {"common_nouns": 0, "proper_nouns": 0}
        return {
            "common_nouns": sum(token.pos_ == "NOUN" for token in self.doc),
            "proper_nouns": sum(token.pos_ == "PROPN" for token in self.doc),
        }

    def common_noun_count(self):
        return self.pos_counts["common_nouns"]

    def proper_noun_count(self):
        return self.pos_counts["proper_nouns"]

    def common_noun_ratio(self):
        return self.common_noun_count() / len(self.words) if self.words else 0

    def proper_noun_ratio(self):
        return self.proper_noun_count() / len(self.words) if self.words else 0

    def relative_clause_count(self): return self.syntax["relative_clauses"] if self.syntax else 0
    def subordinate_clause_count(self): return self.syntax["subordinate_clauses"] if self.syntax else 0
    def nominal_sentence_count(self): return self.syntax["nominal_sentence_count"] if self.syntax else 0
    def relative_clause_ratio(self): return self.relative_clause_count() / len(self.sentences) if self.sentences else 0
    def subordinate_clause_ratio(self): return self.subordinate_clause_count() / len(self.sentences) if self.sentences else 0

    @cached_property
    def lexical_lemma_values(self):
        return lexical_lemmas(self.words)[0]

    def lemma_count(self): return len(self.lexical_lemma_values)
    def lexical_word_count(self): return len(self.lexical_lemma_values)
    def distinct_form_count(self): return len(set(self.words))
    def morphalou_recognized_count(self):
        mapping = lexical_map(self.words)
        forms = [word for word in self.words if not _is_function_word(word, mapping.get(word, (word, ""))[1])]
        lemmas = lemma_map(forms)
        return sum(form in lemmas for form in forms)
    def unique_lemma_count(self): return len(set(self.lexical_lemma_values))
    def hapax_count(self):
        return sum(count == 1 for count in Counter(self.lexical_lemma_values).values())
    def lemma_diversity_ratio(self):
        return self.unique_lemma_count() / self.word_count() if self.word_count() else 0
    def type_token_ratio(self): return len(set(self.words)) / len(self.words) if self.words else 0
    @cached_property
    def lexical_word_blocks(self):
        return [self.words[start:start + ANALYSIS_WINDOW_WORDS]
                for start in range(0, len(self.words), ANALYSIS_WINDOW_WORDS)]

    def moving_type_token_ratio(self):
        ratios = [len(set(block)) / len(block) for block in self.lexical_word_blocks if block]
        return sum(ratios) / len(ratios) if ratios else 0
    def global_lemma_richness(self):
        return self.unique_lemma_count() / self.lexical_word_count() if self.lexical_word_count() else 0
    def lemma_richness(self):
        ratios = []
        for block in self.lexical_word_blocks:
            lemmas = lexical_lemmas(block)[0]
            if lemmas:
                ratios.append(len(set(lemmas)) / len(lemmas))
        return sum(ratios) / len(ratios) if ratios else 0
    def morphalou_coverage(self):
        return self.morphalou_recognized_count() / self.lexical_word_count() if self.lexical_word_count() else 0
    def repetition_word_count(self): return len(self.repetition_words)
    def global_repetition_count(self):
        return repetition_count(self.repetition_words, filtered=True)
    def local_repetition_count(self):
        # Même découpage exhaustif que pour les répétitions phonétiques.
        return sum(repetition_count(self.repetition_words[start:start + ANALYSIS_WINDOW_WORDS], filtered=True)
                   for start in range(0, len(self.repetition_words), ANALYSIS_WINDOW_WORDS))
    def global_repetition_ratio(self):
        return self.global_repetition_count() / self.repetition_word_count() if self.repetition_word_count() else 0
    def local_repetition_ratio(self):
        return self.local_repetition_count() / self.repetition_word_count() if self.repetition_word_count() else 0
    def global_phonetic_repetition_count(self):
        return phonetic_repetition_count(self.repetition_words)
    def local_phonetic_repetition_count(self):
        # Parcourt le document entier, bloc après bloc ; le slicing inclut
        # naturellement le dernier bloc même s'il contient moins de 1 000 mots.
        return sum(phonetic_repetition_count(self.repetition_words[start:start + ANALYSIS_WINDOW_WORDS])
                   for start in range(0, len(self.repetition_words), ANALYSIS_WINDOW_WORDS))
    def global_phonetic_repetition_ratio(self):
        return self.global_phonetic_repetition_count() / self.repetition_word_count() if self.repetition_word_count() else 0
    def local_phonetic_repetition_ratio(self):
        return self.local_phonetic_repetition_count() / self.repetition_word_count() if self.repetition_word_count() else 0
    def absolute_repetition_count(self):
        return repetition_count(self.repetition_words, filtered=False)
    def absolute_repetition_rate(self):
        return self.absolute_repetition_count() / self.repetition_word_count() if self.repetition_word_count() else 0
    def trigram_repetition(self): return _trigram_repetition(self.trigram_lemma_values)

    def verb_count(self): return self.syntax["pos_counts"]["all_verbs"] if self.syntax else 0
    def conjugue_verb_count(self): return self.syntax["all_finite_verbs"] if self.syntax else 0
    def adjective_count(self): return self.syntax["pos_counts"]["adjectives"] if self.syntax else 0
    def adverb_count(self): return self.syntax["pos_counts"]["adverbs"] if self.syntax else 0
    def present_participe_count(self): return self.syntax["present_participles"] if self.syntax else 0
    def past_participe_count(self): return self.syntax["past_participles"] if self.syntax else 0
    def simple_past_count(self): return self.syntax["simple_past"] if self.syntax else 0
    def va_count(self): return self.syntax["periphrastic_future"] if self.syntax else 0
    def future_count(self): return self.syntax["simple_future"] if self.syntax else 0
    def subjonctive_count(self): return self.syntax["literary_subjunctive"] if self.syntax else 0
    def negation_count(self): return self.syntax["negation_total"] if self.syntax else 0
    def verb_negation_count(self): return self.syntax["negation_with_ne"] if self.syntax else 0
    def dialog_word_count(self): return self.syntax["dialog_word_count"] if self.syntax else 0
    def active_sentence_count(self): return self.syntax["active_sentence_count"] if self.syntax else 0
    def passive_sentence_count(self): return self.syntax["passive_sentence_count"] if self.syntax else 0
    def methaphore_count(self): return self.syntax["comparison_sentence_count"] if self.syntax else 0
    def concrate_noun_count(self): return self.syntax["concrete_noun_count"] if self.syntax else 0
    def active_verb_count(self): return self.syntax["action_verb_count"] if self.syntax else 0
    def narrative_verb_count(self): return self.syntax["narrative_verb_count"] if self.syntax else 0
    def gnomic_present_count(self): return self.syntax["gnomic_present_count"] if self.syntax else 0
    def modal_generalization_count(self): return self.syntax["modal_generalization_count"] if self.syntax else 0
    def abstract_noun_count(self): return abstract_noun_count(self.contextual_tokens)
    def personal_subject_count(self): return self.syntax["personal_subject_count"] if self.syntax else 0
    def analyzed_noun_count(self): return self.syntax["analyzed_noun_count"] if self.syntax else 0
    def heavily_modified_noun_count(self): return self.syntax["heavily_modified_noun_count"] if self.syntax else 0
    def adjective_chain_count(self): return self.syntax["adjective_chain_count"] if self.syntax else 0
    def adjective_in_chain_count(self): return self.syntax["adjective_in_chain_count"] if self.syntax else 0
    def noun_modifier_count(self): return self.syntax["noun_modifier_count"] if self.syntax else 0
    def grammatical_token_count(self): return self.syntax["grammatical_token_count"] if self.syntax else 0
    def grammatical_verb_count(self): return self.syntax["grammatical_verb_count"] if self.syntax else 0
    def incise_count(self): return self.syntax["incise_count"] if self.syntax else 0
    def coordination_accumulation_count(self): return self.syntax["coordination_accumulation_count"] if self.syntax else 0
    def function_word_count(self):
        mapping = lexical_map(self.words)
        return sum(_is_function_word(word, mapping.get(word, (word, ""))[1]) for word in self.words)
    def classifiable_subject_count(self): return self.syntax["classifiable_subject_count"] if self.syntax else 0
    def narrative_past_count(self): return self.syntax["narrative_past_count"] if self.syntax else 0
    def lexical_token_count(self): return self.syntax["lexical_token_count"] if self.syntax else 0
    def tense_shift_count(self): return self.syntax["tense_shift_count"] if self.syntax else 0
    def tense_transition_count(self): return self.syntax["tense_transition_count"] if self.syntax else 0
    def negative_sentence_count(self): return self.syntax["negative_sentence_count"] if self.syntax else 0
    def exclamative_sentence_count(self): return self.syntax["exclamative_sentence_count"] if self.syntax else 0

    def suspention_point_count(self): return self.text.count("…")
    def exclamation_point_count(self): return punctuation_pattern_counts(self.text)["exclamation"]
    def question_mark_count(self): return self.text.count("?")
    def semicolons_count(self): return punctuation_pattern_counts(self.text)["semicolon"]
    def period_count(self): return punctuation_pattern_counts(self.text)["point_final"]
    def comma_count(self): return punctuation_pattern_counts(self.text)["virgule"]
    def colon_count(self): return punctuation_pattern_counts(self.text)["colon"]
    def dash_count(self): return self.text.count("–") + self.text.count("—")
    def parenthesis_count(self): return len(re.findall(r"[()]", self.text))
    def quote_mark_count(self):
        return sum(self.text.count(mark) for mark in ("«", "»", "“", "”", '"'))
    def punctuation_mark_count(self):
        return sum((
            self.period_count(), self.comma_count(), self.colon_count(), self.semicolons_count(),
            self.exclamation_point_count(), self.question_mark_count(), self.suspention_point_count(),
            self.dash_count(), self.parenthesis_count(), self.quote_mark_count(),
        ))
    def temporal_connector_count(self): return connector_count(self.text, TEMPORAL_CONNECTORS_FILE)
    def logical_connector_count(self): return connector_count(self.text, LOGICAL_CONNECTORS_FILE)
    def familiarity_marker_count(self): return oral_familiarity_count(self.text)
    def summary_sentence_count(self): return summary_sentence_count(self.sentences)

    def joy_emotion_count(self): return self.emotion_category_profile["counts"]["joie"]
    def sadness_emotion_count(self): return self.emotion_category_profile["counts"]["tristesse"]
    def fear_emotion_count(self): return self.emotion_category_profile["counts"]["peur"]
    def anger_emotion_count(self): return self.emotion_category_profile["counts"]["colère"]
    def surprise_emotion_count(self): return self.emotion_category_profile["counts"]["surprise"]
    def disgust_emotion_count(self): return self.emotion_category_profile["counts"]["dégoût"]
    def contempt_emotion_count(self): return self.emotion_category_profile["counts"]["mépris"]
    def somatic_emotion_count(self): return self.emotion_category_profile["counts"]["manifestations somatiques"]

    @cached_property
    def emotion_category_intensification_counts(self):
        return emotion_category_intensification_counts(self.doc)

    def joy_intensified_emotion_count(self): return self.emotion_category_intensification_counts["joie"]
    def sadness_intensified_emotion_count(self): return self.emotion_category_intensification_counts["tristesse"]
    def fear_intensified_emotion_count(self): return self.emotion_category_intensification_counts["peur"]
    def anger_intensified_emotion_count(self): return self.emotion_category_intensification_counts["colère"]
    def surprise_intensified_emotion_count(self): return self.emotion_category_intensification_counts["surprise"]
    def disgust_intensified_emotion_count(self): return self.emotion_category_intensification_counts["dégoût"]
    def contempt_intensified_emotion_count(self): return self.emotion_category_intensification_counts["mépris"]
    def somatic_intensified_emotion_count(self): return self.emotion_category_intensification_counts["manifestations somatiques"]

    @cached_property
    def sentence_lemmas(self):
        """Phrases lemmatisées en un seul accès groupé à Morphalou."""
        tokenized = [tokenize(sentence) for sentence in self.sentences]
        forms = [word for sentence in tokenized for word in sentence]
        mapping = lemma_map(forms)
        return [tuple(mapping.get(word, word) for word in sentence) for sentence in tokenized]

    @cached_property
    def emotion_category_profile(self):
        return emotion_category_profile(self.sentence_lemmas)

    def emotion_sentence_ratio(self):
        return emotion_sentence_ratio(self.sentence_lemmas)

    def emotion_sentence_count(self):
        return emotion_sentence_count(self.sentence_lemmas)

    def emotion_word_ratio(self):
        return emotion_word_ratio(self.words)

    def emotion_word_count(self):
        return emotion_word_count_from_lemmas(self.lexical_lemma_values)


    def intensifier_adjective_ratio(self):
        return intensifier_adjective_ratio(self.doc)

    def intensified_adjective_count(self):
        return intensified_adjective_count(self.doc)

    def utf8_byte_count(self):
        return len(self.text.encode("utf-8"))

    def gzip_byte_count(self):
        encoded = self.text.encode("utf-8")
        return len(gzip.compress(encoded, mtime=0)) if encoded else 0

    def syllable_count(self):
        return sum(_syllables(word) for word in self.words)


    def emotion_intensification_ratio(self):
        return emotion_intensification_ratio(self.doc)

    def joy_emotion_ratio(self):
        return self.emotion_category_profile["joie"]

    def sadness_emotion_ratio(self):
        return self.emotion_category_profile["tristesse"]

    def fear_emotion_ratio(self):
        return self.emotion_category_profile["peur"]

    def anger_emotion_ratio(self):
        return self.emotion_category_profile["colère"]

    def surprise_emotion_ratio(self):
        return self.emotion_category_profile["surprise"]

    def disgust_emotion_ratio(self):
        return self.emotion_category_profile["dégoût"]

    def contempt_emotion_ratio(self):
        return self.emotion_category_profile["mépris"]

    def somatic_emotion_ratio(self):
        return self.emotion_category_profile["manifestations somatiques"]

    def emotional_category_entropy(self):
        return self.emotion_category_profile["entropy"]

    def ellipsis_ratio(self):
        return ellipsis_ratio(self.text, len(self.sentences))

    def question_mark_ratio(self):
        return question_mark_ratio(self.text, len(self.sentences))

    def emotionality_score(self):
        return sum(
            weight * (
                (self.shared_metrics[field] or 0)
                if field in self.shared_metrics
                else (getattr(self, field)() or 0)
            )
            for field, weight in EMOTIONALITY_WEIGHTS.items()
        )

    def classicism_score(self):
        if all(field in self.shared_metrics for field in CLASSICISM_WEIGHTS):
            values = dict(self.shared_metrics)
            values["oral_familiarity_ratio"] = min((values["oral_familiarity_ratio"] or 0) / 10, 1)
            return sum(CLASSICISM_WEIGHTS[field] * (values[field] or 0) for field in CLASSICISM_WEIGHTS)
        syntax = self.syntax
        narrative_text = self.text
        if self.dialogue_ranges:
            chars = list(self.text)
            for start, end in self.dialogue_ranges:
                chars[start:end] = [" "] * (end - start)
            narrative_text = "".join(chars)
        if syntax:
            verb_ratio_value = syntax["pos_distribution"]["verbs"]
            literary_ratio = syntax.get("literary_subjunctive", 0) / syntax["finite_verbs"] if syntax.get("finite_verbs") else 0
            future_ratio = syntax.get("periphrastic_future_ratio") or 0
            active_ratio = syntax.get("active_voice_ratio") or 0
            dialogue_ratio_value = syntax.get("dialogue_ratio", 0)
        else:
            _, verb_ratio_value, _, _ = _grammatical_ratios(self.words)
            literary_ratio = future_ratio = active_ratio = dialogue_ratio_value = 0
        structures = sentence_structure_signatures(split_structure_units(self.text))
        return (
            CLASSICISM_WEIGHTS["literary_subjunctive_ratio"] * literary_ratio
            + CLASSICISM_WEIGHTS["periphrastic_future_ratio"] * future_ratio
            + CLASSICISM_WEIGHTS["oral_familiarity_ratio"] * min(oral_familiarity_ratio(narrative_text) / 10, 1)
            + CLASSICISM_WEIGHTS["structural_diversity"] * structural_diversity(structures)
            + CLASSICISM_WEIGHTS["verb_ratio"] * verb_ratio_value
            + CLASSICISM_WEIGHTS["active_voice_ratio"] * active_ratio
            + CLASSICISM_WEIGHTS["dialogue_ratio"] * dialogue_ratio_value
            + CLASSICISM_WEIGHTS["punctuation_variety_score"] * punctuation_variety_score(self.text, len(self.sentences))
        )

    @cached_property
    def sentence_lengths(self): return [len(sentence.strip()) for sentence in self.sentences if sentence.strip()]
    @cached_property
    def sentence_word_lengths(self): return [len(tokenize(sentence)) for sentence in self.sentences if sentence.strip()]
    @cached_property
    def paragraph_word_lengths(self): return [len(tokenize(p)) for p in self.paragraphs]
    @cached_property
    def structures(self): return sentence_structure_signatures(split_structure_units(self.text))
    @cached_property
    def sentence_start_structures(self):
        starts = []
        for signature in self.structures:
            parts = structural_subpatterns(signature)
            if parts:
                starts.append(parts[0])
        return starts
    @cached_property
    def narrative_text(self):
        chars = list(self.text)
        for start, end in self.dialogue_ranges: chars[start:end] = [" "] * (end - start)
        return "".join(chars)
    def _component(self, field):
        return self.shared_metrics[field] if field in self.shared_metrics else getattr(self, field)()

    def word_count(self): return len(self.words)
    def sentence_count(self): return len(self.sentences)
    def paragraph_count(self): return len(self.paragraphs)
    def document_char_count(self): return len(self.text)
    def punctuation_ratio(self): return self.punctuation_mark_count() / self.word_count() if self.word_count() else 0
    def punctuation_diversity(self): return punctuation_diversity(self.text)
    def punctuation_variety_score(self): return (self.semicolons_count()+self.colon_count()+self.dash_count()) / self.sentence_count() if self.sentence_count() else 0
    def structural_diversity(self): return structural_diversity(self.structures)
    def structural_rhythm(self): return structural_rhythm(self.structures)
    def structural_repetition_rate(self): return structural_repetition_rate(self.structures)
    def noun_ratio(self): return (self.common_noun_count()+self.proper_noun_count()) / self.grammatical_token_count() if self.grammatical_token_count() else 0
    def verb_ratio(self): return self.grammatical_verb_count() / self.grammatical_token_count() if self.grammatical_token_count() else 0
    def adjective_ratio(self): return self.adjective_count() / self.grammatical_token_count() if self.grammatical_token_count() else 0
    def adverb_ratio(self): return self.adverb_count() / self.grammatical_token_count() if self.grammatical_token_count() else 0
    def noun_verb_ratio(self): return (self.common_noun_count()+self.proper_noun_count()) / self.grammatical_verb_count() if self.grammatical_verb_count() else 0
    def function_word_ratio(self): return self.function_word_count() / self.word_count() if self.word_count() else 0
    def nominal_sentence_ratio(self): return self.nominal_sentence_count() / self.sentence_count() if self.sentence_count() else 0
    def active_voice_ratio(self): return self.active_sentence_count() / self.sentence_count() if self.sentence_count() else 0
    def average_syntactic_depth(self): return self.syntax.get("average_depth", 0) if self.syntax else 0
    def avg_modifiers_per_noun(self): return self.noun_modifier_count() / self.analyzed_noun_count() if self.analyzed_noun_count() else 0
    def heavily_modified_noun_ratio(self): return self.heavily_modified_noun_count() / self.analyzed_noun_count() if self.analyzed_noun_count() else 0
    def adjective_chain_ratio(self): return self.adjective_chain_count() / self.sentence_count() if self.sentence_count() else 0
    def avg_adjective_chain_length(self): return self.adjective_in_chain_count() / self.adjective_chain_count() if self.adjective_chain_count() else 0
    def incise_density(self): return self.incise_count() / self.sentence_count() if self.sentence_count() else 0
    def coordination_accumulation_ratio(self): return self.coordination_accumulation_count() / self.sentence_count() if self.sentence_count() else 0
    def hapax_ratio(self): return self.hapax_count() / self.unique_lemma_count() if self.unique_lemma_count() else 0
    def lexical_rarity_score(self): return lexical_rarity_score(self.words)
    def sentence_start_diversity(self):
        counts = Counter(self.sentence_start_structures)
        total = sum(counts.values())
        if total < 2:
            return 0.0
        identical_pairs = sum(count * (count - 1) for count in counts.values())
        return 1.0 - identical_pairs / (total * (total - 1))
    def sentence_start_recurrence_distance(self):
        previous_positions = {}
        gaps = []
        for position, structure in enumerate(self.sentence_start_structures):
            if structure in previous_positions:
                gaps.append(position - previous_positions[structure])
            previous_positions[structure] = position
        return sum(gaps) / len(gaps) if gaps else 0.0
    def avg_word_length(self): return sum(map(len,self.words))/self.word_count() if self.word_count() else 0
    def avg_sentence_length(self): return sum(self.sentence_word_lengths)/len(self.sentence_word_lengths) if self.sentence_word_lengths else 0
    def median_sentence_length(self): return _percentile(self.sentence_word_lengths,.5)
    def sentence_length_p10(self): return _percentile(self.sentence_word_lengths,.1)
    def sentence_length_p90(self): return _percentile(self.sentence_word_lengths,.9)
    def sentence_length_amplitude(self): return self.sentence_length_p90()-self.sentence_length_p10()
    def sentence_length_std_dev(self): return _std(self.sentence_word_lengths)
    def avg_paragraph_length(self): return sum(self.paragraph_word_lengths)/len(self.paragraph_word_lengths) if self.paragraph_word_lengths else 0
    def paragraph_length_std_dev(self): return _std(self.paragraph_word_lengths)
    def burstiness(self):
        return (sum(abs(b-a) for a,b in zip(self.sentence_word_lengths,self.sentence_word_lengths[1:]))/(len(self.sentence_word_lengths)-1)/self.avg_sentence_length()) if len(self.sentence_word_lengths)>1 and self.avg_sentence_length() else 0
    def gzip_compression_ratio(self): return self.gzip_byte_count()/self.utf8_byte_count() if self.utf8_byte_count() else 0
    def flesch(self): return 207-1.015*(self.word_count()/max(1,self.sentence_count()))-73.6*(self.syllable_count()/self.word_count()) if self.word_count() else 0
    def metaphorical_comme_ratio(self): return self.methaphore_count()/self.sentence_count() if self.sentence_count() else 0
    def present_participle_ratio(self): return self.present_participe_count()/self.word_count() if self.word_count() else 0
    def past_participle_ratio(self): return self.past_participe_count()/self.word_count() if self.word_count() else 0
    def simple_past_ratio(self): return self.simple_past_count()/self.narrative_verb_count() if self.narrative_verb_count() else 0
    def literary_subjunctive_ratio(self): return self.subjonctive_count()/self.narrative_verb_count() if self.narrative_verb_count() else 0
    def negation_completeness_ratio(self): return self.verb_negation_count()/self.negation_count() if self.negation_count() else 0
    def periphrastic_future_ratio(self):
        total=self.va_count()+self.future_count(); return self.va_count()/total if total else 0
    def oral_familiarity_ratio(self): return oral_familiarity_count(self.narrative_text)/self.word_count()*100 if self.word_count() else 0
    def action_verb_ratio(self): return self.active_verb_count()/self.narrative_verb_count() if self.narrative_verb_count() else 0
    def temporal_connector_ratio(self): return self.temporal_connector_count()/self.sentence_count()*100 if self.sentence_count() else 0
    def personal_subject_ratio(self): return self.personal_subject_count()/self.classifiable_subject_count() if self.classifiable_subject_count() else 0
    def narrative_past_ratio(self): return self.narrative_past_count()/self.narrative_verb_count() if self.narrative_verb_count() else 0
    def dialogue_ratio(self): return self.dialog_word_count()/self.word_count() if self.word_count() else 0
    def proper_noun_density(self): return self.proper_noun_count()/self.lexical_token_count() if self.lexical_token_count() else 0
    def concrete_noun_ratio(self): return self.concrate_noun_count()/self.common_noun_count() if self.common_noun_count() else 0
    def tense_shift_rate(self): return self.tense_shift_count()/self.tense_transition_count() if self.tense_transition_count() else 0
    def scene_summary_ratio(self): return self.summary_sentence_count()/self.sentence_count() if self.sentence_count() else 0
    def negation_ratio(self): return self.negative_sentence_count()/self.sentence_count() if self.sentence_count() else 0
    def exclamation_ratio(self): return self.exclamation_point_count()/self.sentence_count() if self.sentence_count() else 0
    def exclamative_construction_ratio(self): return self.exclamative_sentence_count()/self.sentence_count() if self.sentence_count() else 0
    def logical_connector_ratio(self): return self.logical_connector_count()/self.sentence_count()*100 if self.sentence_count() else 0
    def abstract_noun_ratio(self): return self.abstract_noun_count()/self.common_noun_count() if self.common_noun_count() else 0
    def gnomic_present_ratio(self): return self.gnomic_present_count()/self.conjugue_verb_count() if self.conjugue_verb_count() else 0
    def modal_generalization_ratio(self): return self.modal_generalization_count()/self.verb_count() if self.verb_count() else 0

    def baroque_score(self):
        scales={"sentence_start_recurrence_distance":20,"right_branching_depth":10}
        return sum(w*min(self._component(f)/scales.get(f,1),1) for f,w in ORNATENESS_WEIGHTS.items())
    def narrativity_score(self):
        return sum(w*(min(self._component(f)/20,1) if f=="temporal_connector_ratio" else self._component(f)) for f,w in NARRATIVITY_WEIGHTS.items())
    def discursivite_score(self):
        return sum(w*(min(self._component(f)/100,1) if f=="logical_connector_ratio" else self._component(f)) for f,w in DISCURSIVITE_WEIGHTS.items())

    def right_branching_depth(self):
        """Calcule uniquement cette mesure, par lots de phrases.

        Ce chemin évite de lancer les cent autres mesures lors d'une purge
        ciblée et rend visible l'avancement du traitement spaCy.
        """
        pipeline = _pipeline()
        if pipeline is None:
            return 0.0
        sentences = self.sentences
        total = len(sentences)
        if not total:
            return 0.0
        batch_size = 64
        depth_sum = 0.0
        done = 0
        if self.progress:
            self.progress(0, total, "right_branching_depth — phrases")
        for doc in pipeline.pipe(sentences, batch_size=batch_size):
            depth_sum += _right_branching_depth(doc)
            done += 1
            if self.progress and (done == total or done % batch_size == 0):
                self.progress(done, total, "right_branching_depth — phrases")
        return depth_sum / total


FUNCTION_WORDS, GRAMMATICAL_CATEGORIES, FUNCTION_LEMMAS, KEPT_WORDS = _load_function_words()


def _load_familiarity_markers() -> tuple[set[str], set[str]]:
    """Charge les marqueurs oraux : ``direct: mot`` et ``positionnel: mot``."""
    direct, positional = set(), set()
    if not FAMILIARITY_MARKERS_FILE.exists():
        return direct, positional
    for raw in FAMILIARITY_MARKERS_FILE.read_text(encoding=TEXT_ENCODING).splitlines():
        line = raw.strip().lower()
        if not line or line.startswith("#"):
            continue
        kind, separator, value = line.partition(":")
        if not separator or not value.strip():
            continue
        target = positional if kind.strip() in {"position", "positionnel", "positional"} else direct
        target.add(value.strip().replace("’", "'"))
    return direct, positional


FAMILIARITY_DIRECT, FAMILIARITY_POSITIONAL = _load_familiarity_markers()


def lexical_rarity_score(words: list[str]) -> float:
    lemmas, _ = lexical_lemmas(words)
    frequencies = frequency_map(tuple(lemmas))
    # Les fréquences supérieures à 1 par million sont ramenées à une
    # rareté nulle : une rareté ne peut pas devenir négative.
    rarities = [max(0.0, -math.log10(max(frequencies.get(lemma, 0.01), 0.01))) for lemma in lemmas]
    return sum(rarities) / len(rarities) if rarities else 0


def _load_simple_markers(path):
    try:
        return [line.split(":", 1)[-1].strip().casefold() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")]
    except OSError:
        return []


def temporal_connector_ratio(text: str, sentence_count: int) -> float:
    return connector_count(text, TEMPORAL_CONNECTORS_FILE) / sentence_count * 100 if sentence_count else 0


def logical_connector_ratio(text: str, sentence_count: int) -> float:
    """Occurrences de connecteurs logiques pour 100 phrases."""
    return connector_count(text, LOGICAL_CONNECTORS_FILE) / sentence_count * 100 if sentence_count else 0


def connector_count(text: str, path) -> int:
    normalized = text.casefold().replace("’", "'")
    return sum(normalized.count(marker) for marker in _load_simple_markers(path))


def scene_summary_ratio(sentences: list[str], duration_markers: set[str] | None = None, max_sentence_length: int | None = None) -> float:
    markers = duration_markers if duration_markers is not None else set(_load_simple_markers(DURATION_MARKERS_FILE))
    return summary_sentence_count(sentences, markers) / len(sentences) if sentences else 0.0


def summary_sentence_count(sentences: list[str], duration_markers: set[str] | None = None) -> int:
    markers = duration_markers if duration_markers is not None else set(_load_simple_markers(DURATION_MARKERS_FILE))
    return sum(any(marker in sentence.casefold() for marker in markers) for sentence in sentences)


def abstract_noun_ratio(contextual_tokens) -> float:
    suffixes = ("tion", "sion", "isme", "ité", "esse", "ance", "ence", "ure")
    nouns = [token for token in (contextual_tokens or []) if token[2] == "nom"]
    return abstract_noun_count(contextual_tokens) / len(nouns) if nouns else 0.0


def abstract_noun_count(contextual_tokens) -> int:
    suffixes = ("tion", "sion", "isme", "ité", "esse", "ance", "ence", "ure")
    return sum(token[0].casefold().endswith(suffixes) for token in (contextual_tokens or []) if token[2] == "nom")


INTENSIFIER_LEMMAS = {
    "si", "tellement", "tant", "très", "extrêmement", "terriblement",
    "affreusement", "profondément", "particulièrement", "incroyablement",
    "infiniment", "absolument", "fort", "vraiment",
}


def intensifier_adjective_ratio(doc) -> float:
    """Part des adjectifs modifiés par un adverbe d'intensité."""
    if doc is None:
        return 0.0
    adjectives = [token for token in doc if token.pos_ == "ADJ"]
    return intensified_adjective_count(doc) / len(adjectives) if adjectives else 0.0


def intensified_adjective_count(doc) -> int:
    """Nombre d'adjectifs modifiés par un adverbe d'intensité."""
    if doc is None:
        return 0
    intensified = 0
    adjectives = [token for token in doc if token.pos_ == "ADJ"]
    for adjective in adjectives:
        preceding = doc[adjective.i - 1] if adjective.i > 0 else None
        immediate = preceding is not None and preceding.lemma_.casefold() in INTENSIFIER_LEMMAS
        dependent = any(
            child.dep_ == "advmod" and child.lemma_.casefold() in INTENSIFIER_LEMMAS
            for child in adjective.children
        )
        intensified += immediate or dependent
    return intensified


def punctuation_pattern_counts(text: str) -> dict[str, int]:
    return {"point_final": len(re.findall(r"\.", text)), "virgule": len(re.findall(r",", text)),
            "semicolon": len(re.findall(r";", text)), "colon": len(re.findall(r":", text)),
            "exclamation": len(re.findall(r"!", text)), "suspension": text.count("…")}


def punctuation_mark_count(text: str) -> int:
    """Somme des dix compteurs élémentaires de ponctuation."""
    counts = punctuation_pattern_counts(text)
    return sum((
        counts["point_final"], counts["virgule"], counts["colon"], counts["semicolon"],
        counts["exclamation"], text.count("?"), counts["suspension"],
        text.count("–") + text.count("—"), len(re.findall(r"[()]", text)),
        sum(text.count(mark) for mark in ("«", "»", "“", "”", '"')),
    ))


def exclamation_ratio(text: str, sentence_count: int) -> float:
    return punctuation_pattern_counts(text)["exclamation"] / sentence_count if sentence_count else 0.0


def ellipsis_ratio(text: str, sentence_count: int) -> float:
    return punctuation_pattern_counts(text)["suspension"] / sentence_count if sentence_count else 0.0


def question_mark_ratio(text: str, sentence_count: int) -> float:
    """Points d'interrogation rapportés à toutes les phrases."""
    return text.count("?") / sentence_count if sentence_count else 0.0


def punctuation_variety_score(text: str, sentence_count: int) -> float:
    """Nombre de points-virgules, deux-points et tirets longs par phrase."""
    counts = punctuation_pattern_counts(text)
    dashes = text.count("–") + text.count("—")
    return (counts["semicolon"] + counts["colon"] + dashes) / sentence_count if sentence_count else 0.0


def emotion_word_ratio(words: list[str]) -> float:
    lemmas, _ = lexical_lemmas(words)
    return emotion_word_count_from_lemmas(lemmas) / len(lemmas) if lemmas else 0.0


def emotion_word_count_from_lemmas(lemmas: list[str]) -> int:
    emotional_lemmas, phrases = emotional_lemma_patterns()
    count = 0
    index = 0
    while index < len(lemmas):
        lemma = lemmas[index]
        phrase = next(
            (pattern for pattern in phrases.get(lemma, ()) if tuple(lemmas[index:index + len(pattern)]) == pattern),
            None,
        )
        if phrase:
            count += 1
            index += len(phrase)
        else:
            count += int(lemma in emotional_lemmas)
            index += 1
    return count


EMOTION_CATEGORIES = (
    "joie", "tristesse", "peur", "colère", "surprise", "dégoût",
    "mépris", "manifestations somatiques",
)


@lru_cache(maxsize=1)
def emotional_category_patterns() -> dict[str, tuple[frozenset[str], dict[str, tuple[tuple[str, ...], ...]]]]:
    """Charge les sections du dictionnaire comme huit lexiques lemmatisés."""
    raw_by_category = {category: [] for category in EMOTION_CATEGORIES}
    current_category = None
    for raw_line in EMOTIONS_FILE.read_text(encoding=TEXT_ENCODING).splitlines():
        line = raw_line.strip()
        heading = re.fullmatch(r"#\s*---\s*(.+?)\s*---", line)
        if heading:
            current_category = heading.group(1).strip().casefold()
            if current_category not in raw_by_category:
                raise ValueError(f"Catégorie émotionnelle inconnue dans {EMOTIONS_FILE}: {heading.group(1)!r}")
            continue
        if not line or line.casefold() == "&nbsp;":
            continue
        kind, separator, value = line.partition(":")
        if current_category is None or not separator or kind.strip().casefold() != "lemme" or not value.strip():
            raise ValueError(f"Entrée invalide dans {EMOTIONS_FILE}: {raw_line!r}")
        pattern = tuple(tokenize(value.strip()))
        if pattern:
            raw_by_category[current_category].append(pattern)
    mapping = lemma_map(
        word for patterns in raw_by_category.values() for pattern in patterns for word in pattern
    )
    result = {}
    for category, raw_patterns in raw_by_category.items():
        singles = set()
        phrases: dict[str, list[tuple[str, ...]]] = {}
        for raw_pattern in raw_patterns:
            pattern = tuple(mapping.get(word, word) for word in raw_pattern)
            if len(pattern) == 1:
                singles.add(pattern[0])
            else:
                phrases.setdefault(pattern[0], []).append(pattern)
        families = family_map(singles)
        emotional_families = frozenset().union(*(families.get(lemma, frozenset()) for lemma in singles))
        expanded = frozenset(singles).union(family_lexemes(emotional_families))
        result[category] = (expanded, {
            first: tuple(sorted(patterns, key=len, reverse=True))
            for first, patterns in phrases.items()
        })
    return result


@lru_cache(maxsize=1)
def emotional_lemma_patterns() -> tuple[frozenset[str], dict[str, tuple[tuple[str, ...], ...]]]:
    """Charge et lemmatise les marqueurs du dictionnaire émotionnel."""
    raw_patterns = []
    for raw_line in EMOTIONS_FILE.read_text(encoding=TEXT_ENCODING).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.casefold() == "&nbsp;":
            continue
        kind, separator, value = line.partition(":")
        if not separator or kind.strip().casefold() != "lemme" or not value.strip():
            raise ValueError(f"Entrée invalide dans {EMOTIONS_FILE}: {raw_line!r}")
        pattern = tuple(tokenize(value.strip()))
        if pattern:
            raw_patterns.append(pattern)
    mapping = lemma_map(word for pattern in raw_patterns for word in pattern)
    singles = set()
    phrases: dict[str, list[tuple[str, ...]]] = {}
    for raw_pattern in raw_patterns:
        pattern = tuple(mapping.get(word, word) for word in raw_pattern)
        if len(pattern) == 1:
            singles.add(pattern[0])
        else:
            phrases.setdefault(pattern[0], []).append(pattern)
    families = family_map(singles)
    emotional_families = frozenset().union(*(families.get(lemma, frozenset()) for lemma in singles))
    expanded = frozenset(singles).union(family_lexemes(emotional_families))
    return expanded, {
        first: tuple(sorted(patterns, key=len, reverse=True))
        for first, patterns in phrases.items()
    }


def emotion_category_profile(sentence_lemmas: list[tuple[str, ...]]) -> dict[str, float]:
    """Parts des huit catégories et entropie normalisée de leur distribution."""
    category_patterns = emotional_category_patterns()
    counts = dict.fromkeys(EMOTION_CATEGORIES, 0)
    for lemmas in sentence_lemmas:
        for category, (singles, phrases) in category_patterns.items():
            index = 0
            while index < len(lemmas):
                lemma = lemmas[index]
                phrase = next(
                    (pattern for pattern in phrases.get(lemma, ()) if lemmas[index:index + len(pattern)] == pattern),
                    None,
                )
                if phrase:
                    counts[category] += 1
                    index += len(phrase)
                else:
                    counts[category] += int(lemma in singles)
                    index += 1
    total = sum(counts.values())
    ratios = {category: count / total if total else 0.0 for category, count in counts.items()}
    entropy = -sum(ratio * math.log2(ratio) for ratio in ratios.values() if ratio)
    ratios["entropy"] = entropy if total else 0.0
    ratios["counts"] = counts
    return ratios


def emotion_sentence_ratio(sentence_lemmas: list[tuple[str, ...]]) -> float:
    """Part des phrases contenant un marqueur du dictionnaire émotionnel."""
    if not sentence_lemmas:
        return 0.0
    emotional_lemmas, phrases = emotional_lemma_patterns()
    return emotion_sentence_count(sentence_lemmas) / len(sentence_lemmas)


def emotion_sentence_count(sentence_lemmas: list[tuple[str, ...]]) -> int:
    emotional_lemmas, phrases = emotional_lemma_patterns()
    emotional = 0
    for lemmas in sentence_lemmas:
        found = bool(emotional_lemmas.intersection(lemmas)) or any(
            lemmas[index:index + len(pattern)] == pattern
            for index, lemma in enumerate(lemmas)
            for pattern in phrases.get(lemma, ())
        )
        emotional += int(found)
    return emotional


def emotion_intensification_ratio(doc) -> float:
    """Part des marqueurs émotionnels intensifiés ou qualifiés."""
    if doc is None:
        return 0.0
    intensified_count, emotional_count = emotion_intensification_counts(doc)
    return intensified_count / emotional_count if emotional_count else 0.0


def emotion_intensification_counts(doc) -> tuple[int, int]:
    """Totaux agrégés, calculés depuis les huit catégories."""
    intensified_by_category, emotional_by_category = _emotion_category_intensification_profile(doc)
    return sum(intensified_by_category.values()), sum(emotional_by_category.values())


def emotion_category_intensification_counts(doc) -> dict[str, int]:
    """Comptes bruts des marqueurs intensifiés pour chaque émotion."""
    return _emotion_category_intensification_profile(doc)[0]


def _emotion_category_intensification_profile(doc) -> tuple[dict[str, int], dict[str, int]]:
    if doc is None:
        empty = dict.fromkeys(EMOTION_CATEGORIES, 0)
        return empty.copy(), empty
    category_patterns = emotional_category_patterns()
    tokens = [token for token in doc if token.is_alpha]
    mapping = lemma_map(token.lower_ for token in tokens)
    lemmas = tuple(mapping.get(token.lower_, token.lemma_.casefold()) for token in tokens)
    intensified_counts = dict.fromkeys(EMOTION_CATEGORIES, 0)
    emotional_counts = dict.fromkeys(EMOTION_CATEGORIES, 0)
    for category, (emotional_lemmas, phrases) in category_patterns.items():
        index = 0
        while index < len(tokens):
            lemma = lemmas[index]
            phrase = next(
                (pattern for pattern in phrases.get(lemma, ()) if lemmas[index:index + len(pattern)] == pattern),
                None,
            )
            length = len(phrase) if phrase else 1
            if phrase or lemma in emotional_lemmas:
                marker_tokens = tokens[index:index + length]
                preceding = doc[marker_tokens[0].i - 1] if marker_tokens[0].i > 0 else None
                explicit = preceding is not None and preceding.lemma_.casefold() in INTENSIFIER_LEMMAS
                qualified = any(
                    child.dep_ in {"amod", "advmod"}
                    for token in marker_tokens
                    for child in token.children
                )
                emotional_counts[category] += 1
                intensified_counts[category] += int(explicit or qualified)
                index += length
            else:
                index += 1
    return intensified_counts, emotional_counts
WORD_RE = re.compile(r"[\wÀ-ÖØ-öø-ÿ]+(?:['’][\wÀ-ÖØ-öø-ÿ]+)?", re.UNICODE)
PUNCTUATION_MARK_RE = re.compile(r'[.,;:!?…—–()«»“”"]')
STRUCTURE_TOKEN_RE = re.compile(r"[\wÀ-ÖØ-öø-ÿ]+(?:['’][\wÀ-ÖØ-öø-ÿ]+)?|\.\.\.|[…,.!?;:—–()«»\"-]", re.UNICODE)
STRUCTURE_PUNCTUATION = {",", "."}
IGNORED_STRUCTURE_PUNCTUATION = {"...", "…", "!", "?", ";", ":", "—", "–", "-", "(", ")", "«", "»", '"'}
ELIDED_PREFIXES = {"c", "d", "j", "l", "m", "n", "qu", "s", "t"}
ELIDED_CATEGORIES = {
    "c": "pronom", "d": "préposition", "j": "pronom", "l": "déterminant",
    "m": "pronom", "n": "adverbe", "qu": "conjonction", "s": "pronom", "t": "pronom",
}
SUBORDINATORS = {
    "afin", "ainsi", "alors", "bien", "comme", "comment", "lorsque", "parce",
    "pendant", "pourquoi", "puisque", "quand", "que", "quoique", "si", "tandis",
}
SUBJECT_PRONOUNS = {"ça", "elle", "elles", "il", "ils", "je", "j", "nous", "on", "tu", "vous"}


def _is_function_word(word: str, category: str = "", lemma: str = "") -> bool:
    if word in KEPT_WORDS:
        return False
    return word in FUNCTION_WORDS or lemma in FUNCTION_WORDS or lemma in FUNCTION_LEMMAS or category.lower() in GRAMMATICAL_CATEGORIES or len(word) <= 1


def oral_familiarity_ratio(text: str, word_count: int | None = None) -> float:
    """Pourcentage de mots correspondant à des marqueurs familiers.

    Les marqueurs positionnels ne comptent qu'en incise ou en fin de
    proposition ; les marqueurs directs comptent partout.
    """
    matches = list(WORD_RE.finditer(text))
    words = [match.group(0).lower().replace("’", "'") for match in matches]
    total_words = word_count or len(words)
    if not total_words:
        return 0.0
    return oral_familiarity_count(text) / total_words * 100


def oral_familiarity_count(text: str) -> int:
    matches = list(WORD_RE.finditer(text))
    words = [match.group(0).lower().replace("’", "'") for match in matches]
    count = 0
    for index, word in enumerate(words):
        if word in FAMILIARITY_DIRECT:
            count += 1
        elif word in FAMILIARITY_POSITIONAL:
            following = text[matches[index].end():]
            # approximation robuste sans dépendre du parseur : incise ou fin
            # de proposition signalée par une ponctuation forte.
            if re.match(r"^[,;:.!?]", following.lstrip()):
                count += 1
    return count


def tokenize(text: str) -> list[str]:
    return [w.lower().replace("’", "'") for w in WORD_RE.findall(text)]


def tokenize_repetitions(text: str) -> list[object]:
    """Tokens contextualisés par spaCy, avec repli Morphalou sans contexte."""
    contextual = analyze_contextual_tokens(text)
    if contextual is not None:
        return [token for token in contextual if len(token[0]) >= 2]
    return [word for word in tokenize(text.replace("’", " ").replace("'", " ")) if len(word) >= 2]


def split_sentences(text: str) -> list[str]:
    protected = re.sub(r"\b(M|Mme|Mlle|Dr|Pr|etc|env|vol)\.", lambda m: m.group(0)[:-1] + "․", text, flags=re.I)
    protected = re.sub(r"\b([A-ZÀ-Ý])\.", r"\1․", protected)
    return [s.replace("․", ".").strip() for s in re.split(r"(?<=[.!?])(?:\s+|$)", protected) if s.strip()]


def split_structure_units(text: str) -> list[str]:
    """Découpe syntaxique : ponctuation de fin ou saut de ligne."""
    units = []
    for line in text.splitlines():
        if line.strip():
            units.extend(split_sentences(line))
    return units


def _syllables(word: str) -> int:
    groups = re.findall(r"[aeiouyàâäéèêëîïôöùûüÿœ]+", word.lower())
    return max(1, len(groups))


def _percentile(values: list[int], fraction: float) -> float:
    if not values:
        return 0
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _moving_ttr(words: list[str], window: int = 50) -> float:
    if not words:
        return 0
    if len(words) <= window:
        return len(set(words)) / len(words)
    values = [len(set(words[i:i + window])) / window for i in range(len(words) - window + 1)]
    return sum(values) / len(values)


def lexical_lemmas(words: list[str]) -> tuple[list[str], float]:
    """Retourne les lemmes des mots lexicaux et la couverture de Morphalou."""
    mapping = lexical_map(words)
    lexical_forms = [word for word in words if not _is_function_word(word, mapping.get(word, (word, ""))[1])]
    if not lexical_forms:
        return [], 0
    mapping = lemma_map(lexical_forms)
    lemmas = [mapping.get(form, form) for form in lexical_forms]
    coverage = sum(form in mapping for form in lexical_forms) / len(lexical_forms)
    return lemmas, coverage


def vocabulary_richness(words: list[str]) -> tuple[float, float, float, int, int]:
    """Richesses des lemmes lexicaux et couverture de Morphalou."""
    lemmas, coverage = lexical_lemmas(words)
    if not lemmas:
        return 0, 0, 0, 0, 0
    unique_lemmas = len(set(lemmas))
    global_richness = unique_lemmas / len(lemmas)
    return global_richness, global_richness, coverage, len(lemmas), unique_lemmas


def _trigram_repetition(words: list[str]) -> float:
    grams = Counter(zip(words, words[1:], words[2:]))
    return sum(value > 1 for value in grams.values()) / len(grams) if grams else 0


def _trigram_lemmas(words: list[str], contextual_tokens: list[object] | None = None) -> list[str]:
    """Lemmatise en contexte, avec Morphalou comme repli déterministe."""
    if contextual_tokens and isinstance(contextual_tokens[0], tuple):
        contextual = contextual_lemma_map((token[0], token[2], token[1]) for token in contextual_tokens)
        return [contextual.get(token[0], token[1]) for token in contextual_tokens]
    mapping = lemma_map(words)
    return [mapping.get(word, word) for word in words]


def punctuation_diversity(text: str) -> float:
    patterns = [r"\.", r",", r";", r":", r"\?", r"!", r"[—–]", r"[()]", r"[«»“”\"]", r"…"]
    counts = [len(re.findall(pattern, text)) for pattern in patterns]
    total = sum(counts)
    if not total:
        return 0
    entropy = -sum((count / total) * math.log2(count / total) for count in counts if count)
    return entropy / math.log2(len(patterns))


def _grammatical_ratios(words: list[str]) -> tuple[float, float, float, float]:
    mapping = lexical_map(words)
    categories = [mapping[word][1].lower() for word in words if word in mapping]
    total = len(categories)
    if not total:
        return 0, 0, 0, 0
    nouns = sum(category.startswith("nom") for category in categories)
    verbs = sum(category.startswith("verbe") for category in categories)
    adjectives = sum(category.startswith("adjectif") for category in categories)
    adverbs = sum(category.startswith("adverbe") for category in categories)
    return nouns / total, verbs / total, adjectives / total, adverbs / total


def _function_word_ratio(words: list[str]) -> float:
    mapping = lexical_map(words)
    return sum(_is_function_word(word, mapping.get(word, (word, ""))[1]) for word in words) / len(words) if words else 0


def repetition_rate(items: list[str]) -> float:
    return 1 - len(set(items)) / len(items) if items else 0


def local_repetition_rate(words: list[object], filtered: bool, proximity: int | None = None, mode: str = "lexical") -> float:
    """Part des mots répétés lexicalement, familialement ou phonétiquement."""
    words = [word for word in words if len(word[0] if isinstance(word, tuple) else word) >= 2]
    if not words:
        return 0
    return sum(_repetition_flags(words, filtered, proximity, mode=mode)) / len(words)


def repetition_count(words: list[object], filtered: bool = True) -> int:
    """Compte les occurrences dont le lemme possède un antécédent."""
    plain_words = [item[0] if isinstance(item, tuple) else item for item in words]
    mapping = lexical_map(plain_words)
    seen: set[str] = set()
    repeated = 0
    for item in words:
        if isinstance(item, tuple):
            word, lemma, category, *_ = item
        else:
            word = item
            lemma, category = mapping.get(word, (word, ""))
        if filtered and _is_function_word(word, category, lemma):
            continue
        if lemma in seen:
            repeated += 1
        seen.add(lemma)
    return repeated


def _longest_common_phonetic_sequence(left: str, right: str) -> int:
    left = re.sub(r"[.\s‿-]", "", left)
    right = re.sub(r"[.\s‿-]", "", right)
    previous = [0] * (len(right) + 1)
    longest = 0
    for left_phone in left:
        current = [0]
        for index, right_phone in enumerate(right, 1):
            value = previous[index - 1] + 1 if left_phone == right_phone else 0
            current.append(value)
            longest = max(longest, value)
        previous = current
    return longest


def _phonetic_related(left: frozenset[str], right: frozenset[str]) -> bool:
    for first in left:
        for second in right:
            shared = _longest_common_phonetic_sequence(first, second)
            shortest = min(len(re.sub(r"[.\s‿-]", "", first)), len(re.sub(r"[.\s‿-]", "", second)))
            if shared >= PHONETIC_MIN_SEQUENCE and shortest and shared / shortest >= PHONETIC_MIN_RATIO:
                return True
    return False


def phonetic_repetition_count(words: list[object]) -> int:
    """Compte les échos phonétiques avec un index de séquences phonémiques."""
    plain_words = [item[0] if isinstance(item, tuple) else item for item in words]
    mapping = lexical_map(plain_words)
    pronunciations = phonetic_map(plain_words)
    by_sequence: dict[str, set[str]] = {}
    repeated = 0
    for item in words:
        if isinstance(item, tuple):
            word, lemma, category, *_ = item
        else:
            word = item
            lemma, category = mapping.get(word, (word, ""))
        if _is_function_word(word, category, lemma):
            continue
        current = tuple(pronunciations.get(word, frozenset()))
        candidates: set[str] = set()
        normalized = [re.sub(r"[.\s‿-]", "", pronunciation) for pronunciation in current]
        for pronunciation in normalized:
            for start in range(len(pronunciation) - PHONETIC_MIN_SEQUENCE + 1):
                candidates.update(by_sequence.get(pronunciation[start:start + PHONETIC_MIN_SEQUENCE], ()))
        if current and any(_phonetic_related(frozenset(current), frozenset((candidate,))) for candidate in candidates):
            repeated += 1
        for raw, pronunciation in zip(current, normalized):
            for start in range(len(pronunciation) - PHONETIC_MIN_SEQUENCE + 1):
                by_sequence.setdefault(pronunciation[start:start + PHONETIC_MIN_SEQUENCE], set()).add(raw)
    return repeated


def _repetition_flags(words: list[object], filtered: bool, proximity: int | None, mark_all: bool = False, mode: str = "lexical") -> list[bool]:
    plain_words = [word[0] if isinstance(word, tuple) else word for word in words]
    mapping = lexical_map(plain_words)
    lemmas = [
        item[1] if isinstance(item, tuple) else mapping.get(item, (item, ""))[0]
        for item in words
    ]
    families = family_map(lemmas)
    pronunciations = phonetic_map(plain_words) if mode == "phonetic" else {}
    previous: list[tuple[int, str, str]] = []
    flags = []
    for position, item in enumerate(words):
        if isinstance(item, tuple):
            word, lemma, category, *_ = item
        else:
            word = item
            lemma, category = mapping.get(word, (word, ""))
        if filtered and _is_function_word(word, category, lemma):
            flags.append(False)
            continue
        if proximity is not None:
            previous = [(old_position, old_word, old_lemma) for old_position, old_word, old_lemma in previous if position - old_position <= proximity]
        lemma_families = families.get(lemma, frozenset())
        related = []
        for old_position, old_word, old_lemma in previous:
            if mode == "lexical":
                matches = lemma == old_lemma
            elif mode == "family":
                matches = lemma == old_lemma or bool(lemma_families.intersection(families.get(old_lemma, frozenset())))
            elif mode == "phonetic":
                matches = _phonetic_related(pronunciations.get(word, frozenset()), pronunciations.get(old_word, frozenset()))
            else:
                raise ValueError(f"Mode de répétition inconnu : {mode}")
            if matches:
                related.append(old_position)
        flags.append(bool(related))
        if mark_all:
            for old_position in related:
                flags[old_position] = True
        previous.append((position, word, lemma))
    return flags


def repetition_lemma_annotations(
    words: list[object], filtered: bool = True, proximity: int | None = None
) -> list[tuple[str, bool]]:
    """Associe à chaque mot son lemme et son statut de répétition locale."""
    normalized = [(word[0] if isinstance(word, tuple) else word).lower().replace("’", "'") for word in words]
    mapping = lexical_map(word for word in normalized if len(word) >= 2)
    annotations: list[tuple[str, bool]] = []
    for index, word in enumerate(normalized):
        if len(word) < 2:
            annotations.append((word, False))
            continue
        item = words[index]
        if isinstance(item, tuple):
            _, lemma, category, *_ = item
        else:
            lemma, category = mapping.get(word, (word, ""))
        annotations.append((lemma, False))
    flags = _repetition_flags(words, filtered, proximity, mark_all=True, mode="family")
    return [(lemma, repeated) for (lemma, _), repeated in zip(annotations, flags)]


def all_lemmas(words: list[str]) -> list[str]:
    mapping = lexical_map(words)
    return [mapping.get(word, (word, ""))[0] for word in words]


def filtered_lemmas(words: list[str]) -> list[str]:
    mapping = lexical_map(words)
    result = []
    for word in words:
        data = mapping.get(word)
        if data:
            lemma, category = data
            if _is_function_word(word, category):
                continue
            result.append(lemma)
        elif not _is_function_word(word):
            result.append(word)
    return result


def _structure_tokens(sentence: str) -> list[str]:
    tokens = []
    for raw_token in STRUCTURE_TOKEN_RE.findall(sentence.lower().replace("’", "'")):
        if "'" in raw_token:
            prefix, rest = raw_token.split("'", 1)
            if prefix in ELIDED_PREFIXES and rest:
                tokens.extend((prefix, rest))
                continue
        tokens.append(raw_token)
    return tokens


def sentence_structure_signatures(sentences: list[str]) -> list[str]:
    """Encode toutes les phrases en patrons syntaxiques comparables."""
    sentence_tokens = [_structure_tokens(sentence) for sentence in sentences]
    all_words = [token for tokens in sentence_tokens for token in tokens if token not in STRUCTURE_PUNCTUATION | IGNORED_STRUCTURE_PUNCTUATION]
    mapping = lexical_map(all_words)
    signatures = []
    for words in sentence_tokens:
        tokens = []
        previous_category = ""
        for word_index, word in enumerate(words):
            if word in IGNORED_STRUCTURE_PUNCTUATION:
                continue
            if word in STRUCTURE_PUNCTUATION:
                tokens.append(word)
                previous_category = ""
                continue
            following_categories = [
                mapping.get(candidate, (candidate, ""))[1].lower()
                for candidate in words[word_index + 1:]
                if candidate not in STRUCTURE_PUNCTUATION | IGNORED_STRUCTURE_PUNCTUATION
            ]
            pour_infinitive = word == "pour" and any(category.startswith("verbe") for category in following_categories)
            if word in SUBORDINATORS or pour_infinitive:
                category = "subordination"
            elif word in SUBJECT_PRONOUNS:
                category = "pronom"
            else:
                category = ELIDED_CATEGORIES.get(word, mapping.get(word, (word, "inconnu"))[1].lower())
            if category.startswith("nom"):
                category = "nom"
            elif category.startswith("adjectif"):
                category = "adjectif"
            elif category.startswith("verbe"):
                category = "verbe"
            if category in {"déterminant", "préposition"}:
                continue
            # Morphalou conserve parfois le nom pour une forme ambiguë comme
            # « rigole » ; après un pronom sujet, cette forme est verbale.
            if category == "nom" and previous_category == "pronom":
                category = "verbe"
            # Les suites « il se », « je me » décrivent le même sujet verbal
            # que « il », « je » pour cette comparaison de structures.
            if category == "pronom" and previous_category == "pronom":
                continue
            if category == "verbe" and previous_category == "verbe":
                continue
            tokens.append(category.upper())
            previous_category = category
        if tokens:
            signatures.append(_syntactic_signature(tokens))
    return signatures


def _syntactic_clause(tokens: list[str]) -> list[str]:
    """Résume une proposition grammaticale en rôles syntaxiques."""
    if not tokens:
        return []
    if tokens[0] == "SUBORDINATION":
        return ["PROPOSITION_SUBORDONNÉE"]
    # Une coordination placée après une virgule relie deux propositions
    # principales, mais ne fait pas partie de leur structure interne.
    if tokens[0] == "CONJONCTION":
        tokens = tokens[1:]
        if not tokens:
            return []
    if "VERBE" not in tokens:
        return ["INCONNU"] if tokens == ["INCONNU"] else ["COMPLÉMENT"]
    verb_index = tokens.index("VERBE")
    result = []
    if verb_index:
        result.append("SUJET")
    result.append("VERBE")
    tail = tokens[verb_index + 1:]
    if tail:
        # Une coordination ouvre une nouvelle proposition ; les groupes
        # nominaux, adjectivaux ou inconnus sont ramenés à COMPLÉMENT.
        separators = [index for index, token in enumerate(tail) if token in {"CONJONCTION", "SUBORDINATION"}]
        if separators:
            conjunction = separators[0]
            if tail[:conjunction]:
                result.append("COMPLÉMENT")
            marker = tail[conjunction]
            if marker == "SUBORDINATION":
                result.append("PROPOSITION_SUBORDONNÉE")
            else:
                result.append("CONJONCTION")
                result.extend(_syntactic_clause(tail[conjunction + 1:]))
        else:
            result.append("COMPLÉMENT")
    return result


def _syntactic_signature(tokens: list[str]) -> str:
    result = []
    clause = []
    for token in tokens:
        if token in STRUCTURE_PUNCTUATION:
            result.extend(_syntactic_clause(clause))
            result.append(token)
            clause = []
        else:
            clause.append(token)
    result.extend(_syntactic_clause(clause))
    return " ".join(result)


def structural_repetition_rate(signatures: list[str]) -> float:
    """Part des phrases appartenant à une structure utilisée plusieurs fois."""
    eligible = [signature for signature in signatures if structure_is_eligible(signature)]
    counts = Counter(eligible)
    return sum(count for count in counts.values() if count > 1) / len(eligible) if eligible else 0


def structure_is_eligible(signature: str) -> bool:
    """Écarte les patrons sans information grammaticale autre qu'INCONNU."""
    content = [token for token in signature.split() if token not in STRUCTURE_PUNCTUATION]
    return content != ["INCONNU"]


def structural_subpatterns(signature: str) -> list[str]:
    """Découpe une phrase en patrons de propositions comparables.

    Les subordonnées et coordinations ouvrent une nouvelle unité. Les virgules
    et points restent attachés aux propositions ordinaires ; une subordonnée
    conserve le même patron où qu'elle apparaisse afin que leur empilement soit
    effectivement compté comme une répétition.
    """
    units: list[str] = []
    current: list[str] = []

    def flush(boundary: str | None = None) -> None:
        if current:
            suffix = [boundary] if boundary else []
            unit = " ".join(current + suffix)
            if structure_is_eligible(unit):
                units.append(unit)
            current.clear()

    for token in signature.split():
        if token in STRUCTURE_PUNCTUATION:
            flush(token)
        elif token == "PROPOSITION_SUBORDONNÉE":
            flush()
            units.append(token)
        elif token == "CONJONCTION":
            flush()
            current.append(token)
        else:
            current.append(token)
    flush()
    return units


def _structural_profile_distance(left: tuple, right: tuple) -> float:
    """Distance modérée entre deux comptages de propositions."""
    left_counts, right_counts = dict(left), dict(right)
    left_total, right_total = sum(left_counts.values()), sum(right_counts.values())
    keys = left_counts.keys() | right_counts.keys()
    composition = .5 * sum(abs(
        left_counts.get(key, 0) / left_total - right_counts.get(key, 0) / right_total
    ) for key in keys)
    count_distance = sum(abs(left_counts.get(key, 0) - right_counts.get(key, 0)) for key in keys) / (left_total + right_total)
    # Deux structures minuscules ne suffisent pas à établir une opposition
    # maximale. Le bénéfice des architectures développées progresse jusqu'à
    # douze propositions cumulées, sans rendre leur patron automatiquement unique.
    information_weight = min(1, math.sqrt((left_total + right_total) / 12))
    return (.75 * composition + .25 * count_distance) * information_weight


def structural_diversity(signatures: list[str]) -> float:
    """Distance moyenne modérée entre les profils structurels des phrases."""
    profiles = []
    for signature in signatures:
        if not structure_is_eligible(signature):
            continue
        patterns = structural_subpatterns(signature)
        if not patterns:
            continue
        counts = Counter(patterns)
        profiles.append(tuple(sorted(counts.items())))
    if len(profiles) < 2:
        return 0
    profile_counts = Counter(profiles)
    weighted_distance = 0.0
    unique_profiles = list(profile_counts)
    for left_index, left in enumerate(unique_profiles):
        for right in unique_profiles[left_index + 1:]:
            distance = _structural_profile_distance(left, right)
            weighted_distance += distance * profile_counts[left] * profile_counts[right]
    pair_count = len(profiles) * (len(profiles) - 1) / 2
    return weighted_distance / pair_count


def _sequence_distance(left: list[str], right: list[str]) -> float:
    """Distance d'édition normalisée entre deux suites syntaxiques."""
    if not left and not right:
        return 0
    previous = list(range(len(right) + 1))
    for left_index, left_token in enumerate(left, 1):
        current = [left_index]
        for right_index, right_token in enumerate(right, 1):
            current.append(min(
                current[-1] + 1,
                previous[right_index] + 1,
                previous[right_index - 1] + (left_token != right_token),
            ))
        previous = current
    return previous[-1] / max(len(left), len(right))


def structural_rhythm(signatures: list[str]) -> float:
    """Variation moyenne entre deux structures admissibles consécutives."""
    eligible = [signature.split() for signature in signatures if structure_is_eligible(signature)]
    if len(eligible) < 2:
        return 0
    distances = [_sequence_distance(left, right) for left, right in zip(eligible, eligible[1:])]
    return sum(distances) / len(distances)
