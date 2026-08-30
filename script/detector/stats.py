"""Port Python des métriques de stats.js, adaptées au français."""

from collections import Counter
from dataclasses import dataclass, asdict
from functools import cached_property, lru_cache
import gzip
import math
import re

from .config import (ORNATENESS_WEIGHTS, CLASSICISM_WEIGHTS, NARRATIVITY_WEIGHTS, EMOTIONALITY_WEIGHTS, DISCURSIVITE_WEIGHTS, STATIVE_VERBS_FILE, TEMPORAL_CONNECTORS_FILE, LOGICAL_CONNECTORS_FILE, FAMILIARITY_MARKERS_FILE, AFFECT_VERBS_FILE, EMOTIONAL_INTERJECTIONS_FILE, SOMATIC_NOUNS_FILE, EMOTIONS_FILE,
    FUNCTION_WORDS_FILE, DURATION_MARKERS_FILE, LEXICAL_WINDOW_SIZE, PHONETIC_MIN_RATIO,
    PHONETIC_MIN_SEQUENCE, REPETITION_PROXIMITY_WORDS, STYLISTIC_EXACT_WEIGHT,
    STYLISTIC_FAMILY_WEIGHT, STYLISTIC_LEMMA_WEIGHT, TEXT_ENCODING, METRICS)
from .demonette import family_lexemes, family_map, phonetic_map
from .morphalou import contextual_lemma_map, lemma_map, lexical_map
from .syntax_depth import _pipeline, analyze_contextual_tokens, analyze_syntax, dialogue_char_ranges, right_branching_depth as _right_branching_depth
from .lexical_frequency import frequency_map
from .emotion_lexicon import emotion_map


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
        self._computed = None

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
    def dialogue_ranges(self):
        return dialogue_char_ranges(self.text)

    @cached_property
    def sentence_lemmas(self):
        """Phrases lemmatisées en un seul accès groupé à Morphalou."""
        tokenized = [tokenize(sentence) for sentence in self.sentences]
        forms = [word for sentence in tokenized for word in sentence]
        mapping = lemma_map(forms)
        return [tuple(mapping.get(word, word) for word in sentence) for sentence in tokenized]

    def emotion_sentence_ratio(self):
        return emotion_sentence_ratio(self.sentence_lemmas)

    def interjection_density(self):
        return interjection_density(self.text, len(self.words))

    def intensifier_adjective_ratio(self):
        return intensifier_adjective_ratio(self.doc)

    def somatic_reaction_noun_ratio(self):
        return somatic_reaction_noun_ratio(self.contextual_tokens)

    def ellipsis_ratio(self):
        return ellipsis_ratio(self.text, len(self.sentences))

    def question_mark_narration_ratio(self):
        return question_mark_narration_ratio(self.text, self.dialogue_ranges)

    def emotionality_score(self):
        if all(field in self.shared_metrics for field in EMOTIONALITY_WEIGHTS):
            return sum(EMOTIONALITY_WEIGHTS[field] * (self.shared_metrics[field] or 0) for field in EMOTIONALITY_WEIGHTS)
        return (
            EMOTIONALITY_WEIGHTS["emotion_sentence_ratio"]
            * self.emotion_sentence_ratio()
            + EMOTIONALITY_WEIGHTS["exclamation_ratio"]
            * exclamation_ratio(self.text, len(self.sentences))
            + EMOTIONALITY_WEIGHTS["ellipsis_ratio"]
            * ellipsis_ratio(self.text, len(self.sentences))
            + EMOTIONALITY_WEIGHTS["question_mark_narration_ratio"]
            * question_mark_narration_ratio(self.text, self.dialogue_ranges)
            + EMOTIONALITY_WEIGHTS["intensifier_adjective_ratio"]
            * intensifier_adjective_ratio(self.doc)
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

    def right_branching_depth(self):
        """Calcule uniquement cette mesure, par lots de phrases.

        Ce chemin évite de lancer les cent autres mesures lors d'une purge
        ciblée et rend visible l'avancement du traitement spaCy.
        """
        if self._computed is not None:
            return self._computed.right_branching_depth
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
    normalized = text.casefold().replace("’", "'")
    markers = _load_simple_markers(TEMPORAL_CONNECTORS_FILE)
    return sum(normalized.count(marker) for marker in markers) / sentence_count * 100 if sentence_count else 0


def logical_connector_ratio(text: str, sentence_count: int) -> float:
    """Occurrences de connecteurs logiques pour 100 phrases."""
    normalized = text.casefold().replace("’", "'")
    markers = _load_simple_markers(LOGICAL_CONNECTORS_FILE)
    return sum(normalized.count(marker) for marker in markers) / sentence_count * 100 if sentence_count else 0


def scene_summary_ratio(sentences: list[str], duration_markers: set[str] | None = None, max_sentence_length: int | None = None) -> float:
    markers = duration_markers if duration_markers is not None else set(_load_simple_markers(DURATION_MARKERS_FILE))
    if not sentences:
        return 0.0
    maximum = max_sentence_length or max(map(len, sentences), default=0)
    scores = [float(any(marker in sentence.casefold() for marker in markers)) * (1 - len(sentence) / maximum) if maximum else 0.0 for sentence in sentences]
    return sum(scores) / len(scores)


def abstract_noun_ratio(contextual_tokens) -> float:
    suffixes = ("tion", "sion", "isme", "ité", "esse", "ance", "ence", "ure")
    nouns = [token for token in (contextual_tokens or []) if token[2] == "nom"]
    return sum(token[0].casefold().endswith(suffixes) for token in nouns) / len(nouns) if nouns else 0.0


def _load_affect_verbs() -> set[str]:
    return set(_load_simple_markers(AFFECT_VERBS_FILE))


def affect_verb_ratio(contextual_tokens) -> float:
    """Part des verbes finis dont le lemme décrit une réaction affective."""
    if not contextual_tokens:
        return 0.0
    verbs = [token for token in contextual_tokens if token[2] == "verbe"]
    affect = _load_affect_verbs()
    return sum(token[1].casefold() in affect for token in verbs) / len(verbs) if verbs else 0.0


def interjection_density(text: str, word_count: int) -> float:
    """Occurrences d'interjections émotionnelles par mot."""
    if not word_count:
        return 0.0
    normalized = " ".join(tokenize(text.casefold().replace("’", "'")))
    markers = sorted(set(_load_simple_markers(EMOTIONAL_INTERJECTIONS_FILE)), key=len, reverse=True)
    count = 0
    for marker in markers:
        pattern = rf"(?<!\w){re.escape(marker)}(?!\w)"
        normalized, matches = re.subn(pattern, " ", normalized)
        count += matches
    return count / word_count


def somatic_reaction_noun_ratio(contextual_tokens) -> float:
    """Part des noms communs qui désignent une manifestation somatique."""
    nouns = [token for token in (contextual_tokens or []) if token[2] == "nom"]
    markers = set(_load_simple_markers(SOMATIC_NOUNS_FILE))
    return sum(token[1].casefold() in markers for token in nouns) / len(nouns) if nouns else 0.0


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
    intensified = 0
    for adjective in adjectives:
        preceding = doc[adjective.i - 1] if adjective.i > 0 else None
        immediate = preceding is not None and preceding.lemma_.casefold() in INTENSIFIER_LEMMAS
        dependent = any(
            child.dep_ == "advmod" and child.lemma_.casefold() in INTENSIFIER_LEMMAS
            for child in adjective.children
        )
        intensified += immediate or dependent
    return intensified / len(adjectives) if adjectives else 0.0


def punctuation_pattern_counts(text: str) -> dict[str, int]:
    return {"point_final": len(re.findall(r"\.", text)), "virgule": len(re.findall(r",", text)),
            "semicolon": len(re.findall(r";", text)), "colon": len(re.findall(r":", text)),
            "exclamation": len(re.findall(r"!", text)), "suspension": len(re.findall(r"…|\.\.\.", text))}


def exclamation_ratio(text: str, sentence_count: int) -> float:
    return punctuation_pattern_counts(text)["exclamation"] / sentence_count if sentence_count else 0.0


def ellipsis_ratio(text: str, sentence_count: int) -> float:
    return punctuation_pattern_counts(text)["suspension"] / sentence_count if sentence_count else 0.0


def question_mark_narration_ratio(text: str, dialogue_ranges: list[tuple[int, int]]) -> float:
    """Questions hors dialogue rapportées aux phrases narratives."""
    narrative_chars = list(text)
    for start, end in dialogue_ranges:
        narrative_chars[start:end] = [" "] * (end - start)
    narrative_text = "".join(narrative_chars)
    narrative_sentences = split_sentences(narrative_text)
    return narrative_text.count("?") / len(narrative_sentences) if narrative_sentences else 0.0


def punctuation_variety_score(text: str, sentence_count: int) -> float:
    """Nombre de points-virgules et deux-points par phrase."""
    counts = punctuation_pattern_counts(text)
    return (counts["semicolon"] + counts["colon"]) / sentence_count if sentence_count else 0.0


def emotion_word_ratio(words: list[str]) -> float:
    lemmas, _ = lexical_lemmas(words)
    if not lemmas:
        return 0.0
    tags = emotion_map(tuple(lemmas))
    return sum(bool(tags.get(lemma)) for lemma in lemmas) / len(lemmas)


@lru_cache(maxsize=1)
def emotional_lemma_patterns() -> tuple[frozenset[str], dict[str, tuple[tuple[str, ...], ...]]]:
    """Charge les marqueurs émotionnels simples et composés du dictionnaire."""
    raw_patterns: list[tuple[str, ...]] = []
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
    forms = [word for pattern in raw_patterns for word in pattern]
    mapping = lemma_map(forms)
    singles: set[str] = set()
    phrases: dict[str, list[tuple[str, ...]]] = {}
    for raw_pattern in raw_patterns:
        pattern = tuple(mapping.get(word, word) for word in raw_pattern)
        if len(pattern) == 1:
            singles.add(pattern[0])
        else:
            phrases.setdefault(pattern[0], []).append(pattern)
    families = family_map(singles)
    emotional_families = frozenset().union(*(families.get(lemma, frozenset()) for lemma in singles))
    emotional_lemmas = frozenset(singles).union(family_lexemes(emotional_families))
    return emotional_lemmas, {
        first: tuple(sorted(patterns, key=len, reverse=True))
        for first, patterns in phrases.items()
    }


def emotion_sentence_ratio(sentence_lemmas: list[tuple[str, ...]]) -> float:
    """Part des phrases contenant un marqueur émotionnel lemmatisé."""
    if not sentence_lemmas:
        return 0.0
    emotional_lemmas, phrases = emotional_lemma_patterns()
    emotional = 0
    for lemmas in sentence_lemmas:
        if emotional_lemmas.intersection(lemmas):
            emotional += 1
            continue
        found = any(
            lemmas[index:index + len(pattern)] == pattern
            for index, lemma in enumerate(lemmas)
            for pattern in phrases.get(lemma, ())
        )
        emotional += int(found)
    return emotional / len(sentence_lemmas)
WORD_RE = re.compile(r"[\wÀ-ÖØ-öø-ÿ]+(?:['’][\wÀ-ÖØ-öø-ÿ]+)?", re.UNICODE)
PUNCTUATION_MARK_RE = re.compile(r'[.,;:!?…—–\-()«»"]')
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
    return count / total_words * 100


@dataclass
class TextStats:
    word_count: int = 0
    unique_word_count: float = 0
    sentence_count: int = 0
    paragraph_count: int = 0
    avg_word_length: float = 0
    avg_sentence_length: float = 0
    avg_sentence_word_count: float = 0
    median_sentence_length: float = 0
    sentence_length_p10: float = 0
    sentence_length_p90: float = 0
    sentence_length_amplitude: float = 0
    sentence_length_std_dev: float = 0
    sentence_word_std_dev: float = 0
    burstiness: float = 0
    type_token_ratio: float = 0
    moving_type_token_ratio: float = 0
    global_lemma_richness: float = 0
    lemma_richness: float = 0
    morphalou_coverage: float = 0
    lexical_word_count: int = 0
    unique_lemma_count: int = 0
    hapax_ratio: float = 0
    function_word_ratio: float = 0
    trigram_repetition: float = 0
    moving_trigram_repetition: float = 0
    avg_paragraph_length: float = 0
    paragraph_length_std_dev: float = 0
    punctuation_diversity: float = 0
    punctuation_per_300_words: float = 0
    sentence_start_diversity: float = 0
    noun_ratio: float = 0
    verb_ratio: float = 0
    adjective_ratio: float = 0
    adverb_ratio: float = 0
    noun_verb_ratio: float = 0
    form_lemma_ratio: float = 0
    absolute_repetition_rate: float = 0
    filtered_repetition_rate: float = 0
    family_repetition_rate: float = 0
    phonetic_repetition_rate: float = 0
    stylistic_repetition_rate: float = 0
    structural_repetition_rate: float = 0
    structural_diversity: float = 0
    structural_rhythm: float = 0
    gzip_compression_ratio: float = 0
    average_syntactic_depth: float | None = None
    relative_clause_count: int | None = None
    subordinate_clause_count: int | None = None
    relative_clause_ratio: float | None = None
    subordinate_clause_ratio: float | None = None
    nominal_sentence_count: int | None = None
    nominal_sentence_ratio: float | None = None
    active_voice_ratio: float | None = None
    metaphorical_comme_ratio: float | None = None
    pos_common_noun_ratio: float | None = None
    pos_proper_noun_ratio: float | None = None
    proper_noun_density: float = 0
    concrete_noun_ratio: float = 0
    tense_shift_rate: float = 0
    scene_summary_ratio: float = 0
    punctuation_variety_score: float = 0
    incise_density: float = 0
    coordination_accumulation_ratio: float = 0
    right_branching_depth: float = 0
    modal_generalization_ratio: float = 0
    present_participle_ratio: float | None = None
    past_participle_ratio: float | None = None
    simple_past_ratio: float = 0
    literary_subjunctive_ratio: float = 0
    negation_completeness_ratio: float | None = None
    periphrastic_future_ratio: float | None = None
    oral_familiarity_ratio: float = 0
    classicism_score: float = 0
    dialogue_ratio: float = 0
    negation_ratio: float = 0
    avg_modifiers_per_noun: float = 0
    heavily_modified_noun_ratio: float = 0
    lexical_rarity_score: float = 0
    adjective_chain_ratio: float = 0
    avg_adjective_chain_length: float = 0
    baroque_score: float = 0
    action_verb_ratio: float = 0
    temporal_connector_ratio: float = 0
    personal_subject_ratio: float = 0
    emotion_word_ratio: float = 0
    emotion_sentence_ratio: float = 0
    affect_verb_ratio: float = 0
    interjection_density: float = 0
    intensifier_adjective_ratio: float = 0
    somatic_reaction_noun_ratio: float = 0
    ellipsis_ratio: float = 0
    question_mark_narration_ratio: float = 0
    exclamation_ratio: float = 0
    exclamative_construction_ratio: float = 0
    emotionality_score: float = 0
    logical_connector_ratio: float = 0
    abstract_noun_ratio: float = 0
    gnomic_present_ratio: float | None = None
    narrative_past_ratio: float | None = None
    narrativity_score: float = 0
    discursivite_score: float = 0
    flesch: float = 0
    document_char_count: int = 0

    def to_dict(self): return asdict(self)

    def to_metric_dict(self):
        """Sérialisation avec les noms des méthodes métriques."""
        return asdict(self)

    @classmethod
    def from_metric_dict(cls, values):
        return cls(**values)


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


def lemma_richness_distribution(words: list[str], window: int, step: int | None = None) -> dict[str, float | int]:
    """Distribution déterministe de richesse sur fenêtres lexicales contiguës."""
    lemmas, _ = lexical_lemmas(words)
    if not lemmas or window <= 0 or len(lemmas) < window:
        return {"window": window, "count": 0, "mean": 0, "median": 0, "p10": 0, "p90": 0}
    step = step or max(1, window // 4)
    starts = list(range(0, len(lemmas) - window + 1, step))
    if starts[-1] != len(lemmas) - window:
        starts.append(len(lemmas) - window)
    values = [len(set(lemmas[start:start + window])) / window for start in starts]
    return {
        "window": window, "count": len(values), "mean": sum(values) / len(values),
        "median": _percentile(values, .5), "p10": _percentile(values, .1), "p90": _percentile(values, .9),
    }


def vocabulary_richness(words: list[str], window: int = LEXICAL_WINDOW_SIZE) -> tuple[float, float, float, int, int]:
    """Richesses globale/mobile des lemmes lexicaux et couverture de Morphalou."""
    lemmas, coverage = lexical_lemmas(words)
    if not lemmas:
        return 0, 0, 0, 0, 0
    unique_lemmas = len(set(lemmas))
    global_richness = unique_lemmas / len(lemmas)
    return global_richness, _moving_ttr(lemmas, window), coverage, len(lemmas), unique_lemmas


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


def _moving_trigram_repetition(words: list[str], window: int = 200, step: int = 50) -> float:
    """Répétition moyenne sur fenêtres fixes, comparable entre textes de tailles différentes."""
    if len(words) <= window:
        return _trigram_repetition(words)
    starts = list(range(0, len(words) - window + 1, step))
    if starts[-1] != len(words) - window:
        starts.append(len(words) - window)
    return sum(_trigram_repetition(words[start:start + window]) for start in starts) / len(starts)


def punctuation_diversity(text: str) -> float:
    patterns = [r"\.", r",", r";", r":", r"\?", r"!", r"[—–-]", r"[()]", r"[«»\"]", r"…|\.\.\."]
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


def local_repetition_rate(words: list[object], filtered: bool, proximity: int = REPETITION_PROXIMITY_WORDS, mode: str = "lexical") -> float:
    """Part des mots répétés lexicalement, familialement ou phonétiquement."""
    words = [word for word in words if len(word[0] if isinstance(word, tuple) else word) >= 2]
    if not words:
        return 0
    return sum(_repetition_flags(words, filtered, proximity, mode=mode)) / len(words)


def stylistic_repetition_rate(words: list[object], proximity: int = REPETITION_PROXIMITY_WORDS) -> float:
    """Pression des chaînes répétitives, inspirée du filtre intelligent d’Antidote.

    Chaque paire située dans l’empan vaut 1 si les graphies sont identiques,
    0,25 si seul le lemme ou la famille morphologique coïncide. Les mots-outils
    et les noms propres sont écartés. Le dénominateur reste tous les mots afin
    que la valeur exprime une densité dans le texte.
    """
    if not words:
        return 0
    normalized = []
    plain_words = [item[0] if isinstance(item, tuple) else item for item in words]
    mapping = lexical_map(plain_words)
    for item in words:
        if isinstance(item, tuple):
            word, lemma, category, *_ = item
        else:
            word = item
            lemma, category = mapping.get(word, (word, ""))
        normalized.append((word, lemma, category))
    families = family_map(lemma for _, lemma, _ in normalized)
    pressure = 0.0
    for position, (word, lemma, category) in enumerate(normalized):
        if _is_function_word(word, category, lemma) or category.lower() == "nom propre":
            continue
        for old_word, old_lemma, old_category in normalized[max(0, position - proximity):position]:
            if _is_function_word(old_word, old_category, old_lemma) or old_category.lower() == "nom propre":
                continue
            if word == old_word:
                pressure += STYLISTIC_EXACT_WEIGHT
            elif lemma == old_lemma:
                pressure += STYLISTIC_LEMMA_WEIGHT
            elif families.get(lemma, frozenset()).intersection(families.get(old_lemma, frozenset())):
                pressure += STYLISTIC_FAMILY_WEIGHT
    return min(1.0, pressure / len(words))


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


def _repetition_flags(words: list[object], filtered: bool, proximity: int, mark_all: bool = False, mode: str = "lexical") -> list[bool]:
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
    words: list[object], filtered: bool = True, proximity: int = REPETITION_PROXIMITY_WORDS
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


def _install_metric_methods() -> None:
    """Expose une méthode nommée pour chaque clé de METRICS."""
    for field in METRICS:
        if hasattr(Metrics, field):
            continue
        def metric(self, _field=field):
            if self._computed is None:
                self._computed = _compute_all_stats(self.text, context=self)
            return getattr(self._computed, _field, 0)
        metric.__name__ = field
        setattr(Metrics, field, metric)


_install_metric_methods()


def lemma_hapax_ratio(words: list[str]) -> float:
    """Part des lemmes lexicaux distincts qui n'apparaissent qu'une fois."""
    lemmas = filtered_lemmas(words)
    frequencies = Counter(lemmas)
    return sum(count == 1 for count in frequencies.values()) / len(frequencies) if frequencies else 0


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


def repetition_distribution(words: list[str], window: int, step: int | None = None) -> dict[str, float | int]:
    if not words or window <= 0 or len(words) < window:
        return {"window": window, "count": 0, "absolute": 0, "filtered": 0, "family": 0, "phonetic": 0}
    step = step or window
    starts = list(range(0, len(words) - window + 1, step))
    if starts[-1] != len(words) - window:
        starts.append(len(words) - window)
    absolute_values, filtered_values, family_values, phonetic_values = [], [], [], []
    for start in starts:
        sample = words[start:start + window]
        absolute_values.append(local_repetition_rate(sample, filtered=False, mode="lexical"))
        filtered_values.append(local_repetition_rate(sample, filtered=True, mode="lexical"))
        family_values.append(local_repetition_rate(sample, filtered=True, mode="family"))
        phonetic_values.append(local_repetition_rate(sample, filtered=True, mode="phonetic"))
    average = lambda values: sum(values) / len(values)
    return {"window": window, "count": len(starts), "absolute": average(absolute_values), "filtered": average(filtered_values), "family": average(family_values), "phonetic": average(phonetic_values)}


def _compute_all_stats(text: str, progress=None, context: Metrics | None = None) -> TextStats:
    """Calcule les mesures et signale éventuellement les grandes étapes."""
    def report(step: int, label: str) -> None:
        if progress is not None:
            progress(step, 8, label)

    report(1, "tokenisation")
    context = context or Metrics(text)
    words, sentences = context.words, context.sentences
    repetition_words = context.contextual_tokens
    if repetition_words is not None:
        repetition_words = [token for token in repetition_words if len(token[0]) >= 2]
    else:
        repetition_words = [word for word in tokenize(text.replace("’", " ").replace("'", " ")) if len(word) >= 2]
    if not words: return TextStats()
    # Longueur stylistique des phrases en caractères, espaces compris.
    lengths = [len(s.strip()) for s in sentences if s.strip()]
    sentence_word_lengths = [len(tokenize(sentence)) for sentence in sentences if sentence.strip()]
    mean = sum(lengths) / len(lengths) if lengths else 0
    word_mean = sum(sentence_word_lengths) / len(sentence_word_lengths) if sentence_word_lengths else 0
    std = math.sqrt(sum((n - mean) ** 2 for n in lengths) / len(lengths)) if len(lengths) > 1 else 0
    word_std = math.sqrt(sum((n - word_mean) ** 2 for n in sentence_word_lengths) / len(sentence_word_lengths)) if len(sentence_word_lengths) > 1 else 0
    mean_difference = sum(abs(b-a) for a, b in zip(lengths, lengths[1:])) / (len(lengths)-1) if len(lengths)>1 else 0
    burst = mean_difference / mean if mean else 0
    report(2, "mesures lexicales")
    trigram_lemmas = _trigram_lemmas(words, repetition_words)
    repetition = _trigram_repetition(trigram_lemmas)
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    paragraph_lengths = [len(tokenize(paragraph)) for paragraph in paragraphs]
    paragraph_mean = sum(paragraph_lengths) / len(paragraph_lengths) if paragraph_lengths else 0
    paragraph_std = math.sqrt(sum((length - paragraph_mean) ** 2 for length in paragraph_lengths) / len(paragraph_lengths)) if len(paragraph_lengths) > 1 else 0
    syllables = sum(_syllables(w) for w in words)
    # Flesch français (plus haut = plus lisible), en remplacement du grade anglais.
    flesch = 207 - 1.015 * (len(words) / max(1, len(lengths))) - 73.6 * (syllables / len(words))
    r = lambda x: round(x, 3)
    frequencies = Counter(words)
    global_lemma_richness, lemma_richness, morphalou_coverage, lexical_word_count, unique_lemma_count = vocabulary_richness(words)
    starts = [sentence_words[0] for sentence in sentences if (sentence_words := tokenize(sentence))]
    content_lemmas = filtered_lemmas(words)
    structures = sentence_structure_signatures(split_structure_units(text))
    encoded_text = text.encode("utf-8")
    gzip_ratio = len(gzip.compress(encoded_text, mtime=0)) / len(encoded_text) if encoded_text else 0
    report(3, "analyse syntaxique")
    syntax = context.syntax
    if syntax:
        distribution = syntax["pos_distribution"]
        noun_ratio = distribution["common_nouns"] + distribution["proper_nouns"]
        verb_ratio = distribution["verbs"]
        adjective_ratio = distribution["adjectives"]
        adverb_ratio = distribution["adverbs"]
        pos_total = sum(1 for word in words if word.isalpha()) or 1
        present_participle_ratio = syntax["present_participles"] / pos_total
        past_participle_ratio = syntax["past_participles"] / pos_total
        simple_past_ratio = syntax["simple_past"] / syntax["finite_verbs"] if syntax["finite_verbs"] else 0
        literary_subjunctive_ratio = syntax["literary_subjunctive"] / syntax["finite_verbs"] if syntax["finite_verbs"] else 0
        negation_completeness = syntax["negation_completeness_ratio"]
        periphrastic_future_ratio = syntax["periphrastic_future_ratio"]
    else:
        noun_ratio, verb_ratio, adjective_ratio, adverb_ratio = _grammatical_ratios(words)
        present_participle_ratio = past_participle_ratio = None
        simple_past_ratio = literary_subjunctive_ratio = 0
        negation_completeness = periphrastic_future_ratio = None
    report(4, "dialogues et registres")
    dialogue_ranges = context.dialogue_ranges
    narrative_text = text
    if dialogue_ranges:
        chars = list(text)
        for start, end in dialogue_ranges:
            chars[start:end] = [" "] * (end - start)
        narrative_text = "".join(chars)
    # Les marqueurs familiers des répliques ne décrivent pas la voix
    # narrative : ils sont exclus de cette mesure.
    oral_ratio = oral_familiarity_ratio(narrative_text)
    dialogue_ratio_value = syntax.get("dialogue_ratio", 0) if syntax else 0
    avg_modifiers = syntax.get("avg_modifiers_per_noun", 0) if syntax else 0
    heavily_modified = syntax.get("heavily_modified_noun_ratio", 0) if syntax else 0
    adjective_chain_ratio = syntax.get("adjective_chain_ratio", 0) if syntax else 0
    avg_adjective_chain = syntax.get("avg_adjective_chain_length", 0) if syntax else 0
    report(5, "rareté lexicale")
    lexical_rarity = lexical_rarity_score(words)
    action_ratio = syntax.get("action_verb_ratio", 0) if syntax else 0
    personal_ratio = syntax.get("personal_subject_ratio", 0) if syntax else 0
    temporal_ratio = temporal_connector_ratio(text, len(sentences))
    # Les ratios noun/verb et voix active sont ramenés à des échelles bornées
    # ici pour fournir un score local stable ; le rapport comparatif applique
    # ensuite sa normalisation par percentiles pour les comparaisons.
    active_ratio = syntax["active_voice_ratio"] if syntax and syntax["active_voice_ratio"] is not None else 0
    literary_ratio = literary_subjunctive_ratio
    report(6, "calcul du classicisme")
    classicism = (
        CLASSICISM_WEIGHTS["literary_subjunctive_ratio"] * literary_ratio
        + CLASSICISM_WEIGHTS["periphrastic_future_ratio"] * (periphrastic_future_ratio or 0)
        + CLASSICISM_WEIGHTS["oral_familiarity_ratio"] * min(oral_ratio / 10, 1)
        + CLASSICISM_WEIGHTS["structural_diversity"] * structural_diversity(structures)
        + CLASSICISM_WEIGHTS["verb_ratio"] * verb_ratio
        + CLASSICISM_WEIGHTS["active_voice_ratio"] * active_ratio
        + CLASSICISM_WEIGHTS["dialogue_ratio"] * dialogue_ratio_value
        + CLASSICISM_WEIGHTS["punctuation_variety_score"] * punctuation_variety_score(text, len(sentences))
    )
    baroque = (
        ORNATENESS_WEIGHTS["heavily_modified_noun_ratio"] * heavily_modified
        + ORNATENESS_WEIGHTS["metaphorical_comme_ratio"] * (syntax.get("metaphorical_comme_ratio", 0) if syntax else 0)
        + ORNATENESS_WEIGHTS["adjective_chain_ratio"] * adjective_chain_ratio
        + ORNATENESS_WEIGHTS["avg_sentence_length"] * min(mean / 200, 1)
        + ORNATENESS_WEIGHTS["right_branching_depth"] * min((syntax.get("right_branching_depth", 0) if syntax else 0) / 10, 1)
        + ORNATENESS_WEIGHTS["incise_density"] * (syntax.get("incise_density", 0) if syntax else 0)
        + ORNATENESS_WEIGHTS["coordination_accumulation_ratio"] * (syntax.get("coordination_accumulation_ratio", 0) if syntax else 0)
    )
    report(7, "analyse des marqueurs affectifs")
    contextual_for_affect = context.contextual_tokens
    emotion_ratio = emotion_word_ratio(words)
    emotion_sentence = context.emotion_sentence_ratio()
    affect_ratio = affect_verb_ratio(contextual_for_affect)
    interjection_ratio = interjection_density(text, len(words))
    intensifier_ratio = intensifier_adjective_ratio(context.doc)
    somatic_ratio = somatic_reaction_noun_ratio(contextual_for_affect)
    suspension_ratio = ellipsis_ratio(text, len(sentences))
    narrative_question_ratio = question_mark_narration_ratio(text, dialogue_ranges)
    exclaim_ratio = exclamation_ratio(text, len(sentences))
    exclamative_ratio = syntax.get("exclamative_construction_ratio", 0) if syntax else 0
    emotionality = (
        EMOTIONALITY_WEIGHTS["emotion_sentence_ratio"] * emotion_sentence
        + EMOTIONALITY_WEIGHTS["exclamation_ratio"] * exclaim_ratio
        + EMOTIONALITY_WEIGHTS["ellipsis_ratio"] * suspension_ratio
        + EMOTIONALITY_WEIGHTS["question_mark_narration_ratio"] * narrative_question_ratio
        + EMOTIONALITY_WEIGHTS["intensifier_adjective_ratio"] * intensifier_ratio
    )
    logical_ratio = logical_connector_ratio(text, len(sentences))
    abstract_ratio = abstract_noun_ratio(contextual_for_affect)
    gnomic_ratio = syntax.get("gnomic_present_ratio", 0) if syntax else 0
    noun_verb_normalized = min(noun_ratio / max(verb_ratio, 0.001) / 5, 1)
    past_ratio = syntax.get("narrative_past_ratio", 0) if syntax else 0
    narrativity = (NARRATIVITY_WEIGHTS["action_verb_ratio"] * action_ratio
        + NARRATIVITY_WEIGHTS["temporal_connector_ratio"] * min(temporal_ratio / 20, 1)
        + NARRATIVITY_WEIGHTS["dialogue_ratio"] * dialogue_ratio_value
        + NARRATIVITY_WEIGHTS["active_voice_ratio"] * active_ratio
        + NARRATIVITY_WEIGHTS["tense_shift_rate"] * (syntax.get("tense_shift_rate", 0) if syntax else 0)
        + NARRATIVITY_WEIGHTS["proper_noun_density"] * (syntax.get("proper_noun_density", 0) if syntax else 0)
        + NARRATIVITY_WEIGHTS["nominal_sentence_ratio"] * (syntax.get("nominal_sentence_ratio", 0) if syntax else 0)
        + NARRATIVITY_WEIGHTS["adjective_ratio"] * adjective_ratio)
    # La discursivité repose uniquement sur les marqueurs logiques : les
    # noms, adjectifs et sujets génériques peuvent relever de la description.
    # logical_ratio est calculé sur toutes les phrases du document (le « pour
    # 100 » sert uniquement à l'affichage). On le convertit en proportion pour
    # le score composite, sans fenêtre ni dénominateur arbitraire.
    discursivite = (DISCURSIVITE_WEIGHTS["logical_connector_ratio"] * min(logical_ratio / 100, 1)
                    + DISCURSIVITE_WEIGHTS["abstract_noun_ratio"] * abstract_ratio
                    + DISCURSIVITE_WEIGHTS["gnomic_present_ratio"] * gnomic_ratio)
    report(8, "assemblage des résultats")
    result = TextStats(
        word_count=len(words), unique_word_count=r(unique_lemma_count / len(words)), sentence_count=len(lengths),
        paragraph_count=len(paragraphs), avg_word_length=r(sum(map(len, words)) / len(words)),
        avg_sentence_length=r(mean), avg_sentence_word_count=r(word_mean), median_sentence_length=r(_percentile(lengths, .5)),
        sentence_length_p10=r(_percentile(lengths, .1)), sentence_length_p90=r(_percentile(lengths, .9)),
        sentence_length_amplitude=r(_percentile(lengths, .9) - _percentile(lengths, .1)),
        sentence_length_std_dev=r(std), sentence_word_std_dev=r(word_std),
        burstiness=r(burst), type_token_ratio=r(len(frequencies) / len(words)),
        moving_type_token_ratio=r(_moving_ttr(words)),
        global_lemma_richness=r(global_lemma_richness), lemma_richness=r(lemma_richness),
        morphalou_coverage=r(morphalou_coverage), lexical_word_count=lexical_word_count,
        unique_lemma_count=unique_lemma_count,
        hapax_ratio=r(lemma_hapax_ratio(words)),
        function_word_ratio=r(_function_word_ratio(words)),
        trigram_repetition=r(repetition), moving_trigram_repetition=r(_moving_trigram_repetition(trigram_lemmas)),
        avg_paragraph_length=r(paragraph_mean), paragraph_length_std_dev=r(paragraph_std),
        punctuation_diversity=r(punctuation_diversity(text)),
        punctuation_per_300_words=r(len(PUNCTUATION_MARK_RE.findall(text)) / len(words) * 100),
        sentence_start_diversity=r(_moving_ttr(starts, 20)),
        noun_ratio=r(noun_ratio), verb_ratio=r(verb_ratio), adjective_ratio=r(adjective_ratio),
        adverb_ratio=r(adverb_ratio), noun_verb_ratio=r(noun_ratio / verb_ratio if verb_ratio else 0),
        form_lemma_ratio=r(_moving_ttr(words, LEXICAL_WINDOW_SIZE) / lemma_richness if lemma_richness else 0),
        absolute_repetition_rate=r(local_repetition_rate(repetition_words, filtered=False)),
        filtered_repetition_rate=r(local_repetition_rate(repetition_words, filtered=True)),
        family_repetition_rate=r(local_repetition_rate(repetition_words, filtered=True, mode="family")),
        phonetic_repetition_rate=r(local_repetition_rate(repetition_words, filtered=True, mode="phonetic")),
        stylistic_repetition_rate=r(stylistic_repetition_rate(repetition_words)),
        structural_repetition_rate=r(structural_repetition_rate(structures)),
        structural_diversity=r(structural_diversity(structures)),
        structural_rhythm=r(structural_rhythm(structures)),
        gzip_compression_ratio=r(gzip_ratio),
        average_syntactic_depth=r(syntax["average_depth"]) if syntax else None,
        relative_clause_count=syntax["relative_clauses"] if syntax else None,
        subordinate_clause_count=syntax["subordinate_clauses"] if syntax else None,
        relative_clause_ratio=r(syntax["relative_clause_ratio"]) if syntax else None,
        subordinate_clause_ratio=r(syntax["subordinate_clause_ratio"]) if syntax else None,
        nominal_sentence_count=syntax["nominal_sentence_count"] if syntax else None,
        nominal_sentence_ratio=r(syntax["nominal_sentence_ratio"]) if syntax else None,
        active_voice_ratio=r(syntax["active_voice_ratio"]) if syntax and syntax["active_voice_ratio"] is not None else None,
        metaphorical_comme_ratio=r(syntax["metaphorical_comme_ratio"]) if syntax and syntax["metaphorical_comme_ratio"] is not None else None,
        pos_common_noun_ratio=r(syntax["pos_distribution"]["common_nouns"]) if syntax else None,
        pos_proper_noun_ratio=r(syntax["pos_distribution"]["proper_nouns"]) if syntax else None,
        proper_noun_density=r(syntax.get("proper_noun_density", 0)) if syntax else 0,
        concrete_noun_ratio=r(syntax.get("concrete_noun_ratio", 0)) if syntax else 0,
        tense_shift_rate=r(syntax.get("tense_shift_rate", 0)) if syntax else 0,
        scene_summary_ratio=r(scene_summary_ratio(sentences, max_sentence_length=max(map(len, sentences), default=0))),
        punctuation_variety_score=r(punctuation_variety_score(text, len(sentences))),
        incise_density=r(syntax.get("incise_density", 0)) if syntax else 0,
        coordination_accumulation_ratio=r(syntax.get("coordination_accumulation_ratio", 0)) if syntax else 0,
        right_branching_depth=r(syntax.get("right_branching_depth", 0)) if syntax else 0,
        modal_generalization_ratio=r(syntax.get("modal_generalization_ratio", 0)) if syntax else 0,
        present_participle_ratio=r(present_participle_ratio) if present_participle_ratio is not None else None,
        past_participle_ratio=r(past_participle_ratio) if past_participle_ratio is not None else None,
        simple_past_ratio=r(simple_past_ratio), literary_subjunctive_ratio=r(literary_subjunctive_ratio),
        negation_completeness_ratio=r(negation_completeness) if negation_completeness is not None else None,
        periphrastic_future_ratio=r(periphrastic_future_ratio) if periphrastic_future_ratio is not None else None,
        oral_familiarity_ratio=r(oral_ratio), classicism_score=r(classicism),
        dialogue_ratio=r(dialogue_ratio_value),
        negation_ratio=r(syntax.get("negation_ratio", 0)) if syntax else 0,
        avg_modifiers_per_noun=r(avg_modifiers), heavily_modified_noun_ratio=r(heavily_modified),
        lexical_rarity_score=r(lexical_rarity), adjective_chain_ratio=r(adjective_chain_ratio),
        avg_adjective_chain_length=r(avg_adjective_chain), baroque_score=r(baroque),
        action_verb_ratio=r(action_ratio), temporal_connector_ratio=r(temporal_ratio),
        personal_subject_ratio=r(personal_ratio),
        emotion_word_ratio=r(emotion_ratio), emotion_sentence_ratio=r(emotion_sentence), affect_verb_ratio=r(affect_ratio),
        interjection_density=r(interjection_ratio), intensifier_adjective_ratio=r(intensifier_ratio),
        somatic_reaction_noun_ratio=r(somatic_ratio), ellipsis_ratio=r(suspension_ratio),
        question_mark_narration_ratio=r(narrative_question_ratio), exclamation_ratio=r(exclaim_ratio),
        exclamative_construction_ratio=r(exclamative_ratio), emotionality_score=r(emotionality),
        logical_connector_ratio=r(logical_ratio), abstract_noun_ratio=r(abstract_ratio),
        narrative_past_ratio=r(past_ratio), narrativity_score=r(narrativity), gnomic_present_ratio=r(gnomic_ratio), discursivite_score=r(discursivite),
        flesch=r(flesch), document_char_count=len(text),
    )
    return result


def compute_stats(text: str, progress=None) -> TextStats:
    """API historique construite depuis l'unique registre ``METRICS``.

    La génération ne connaît aucune table de fonctions : elle demande chaque
    mesure à l'objet ``Metrics``. Ses données préparées restent mémorisées et
    sont donc partagées entre tous les appels.
    """
    metrics = Metrics(text)
    values = {}
    for index, field in enumerate(METRICS, 1):
        if progress is not None:
            progress(index, len(METRICS), field)
        values[field] = getattr(metrics, field)()
    return TextStats(**values)


def uniformity_components(s: TextStats, filtered_repetition: float | None = None) -> dict[str, float]:
    """Signaux continus d'uniformité, tous compris entre 0 et 1."""
    clamp = lambda value: max(0, min(value, 1))
    repetition = s.filtered_repetition_rate if filtered_repetition is None else filtered_repetition
    relative_amplitude = s.sentence_length_amplitude / s.avg_sentence_length if s.avg_sentence_length else 0
    return {
        "sentence_amplitude": 1 - clamp(relative_amplitude / 2),
        "burstiness": 1 - clamp(s.burstiness),
        "vocabulary_repetition": clamp(repetition),
        "structure_repetition": clamp(s.structural_repetition_rate),
        "structure_similarity": 1 - clamp(s.structural_diversity),
        "structure_rhythm": 1 - clamp(s.structural_rhythm),
    }


def uniformity_score(s: TextStats, filtered_repetition: float | None = None) -> float:
    components = uniformity_components(s, filtered_repetition)
    return round(sum(components.values()) / len(components) * 100) if components else 0


if __name__ == "__main__":
    from .stats_cli import main

    raise SystemExit(main())
