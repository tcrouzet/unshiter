"""Port Python des métriques de stats.js, adaptées au français."""

from collections import Counter
from dataclasses import dataclass, asdict
import gzip
import math
import re

from .config import FUNCTION_WORDS_FILE, LEXICAL_WINDOW_SIZE, PHONETIC_MIN_RATIO, PHONETIC_MIN_SEQUENCE, REPETITION_PROXIMITY_WORDS, STYLISTIC_EXACT_WEIGHT, STYLISTIC_FAMILY_WEIGHT, STYLISTIC_LEMMA_WEIGHT, TEXT_ENCODING
from .demonette import family_map, phonetic_map
from .morphalou import contextual_lemma_map, lemma_map, lexical_map
from .syntax_depth import analyze_contextual_tokens, analyze_syntax


def _load_function_words() -> tuple[set[str], set[str], set[str], set[str]]:
    """Charge les mots et catégories modifiables depuis assets/function-words.txt."""
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
        else:
            raise ValueError(f"Type inconnu dans {FUNCTION_WORDS_FILE}: {kind!r}")
    return words, categories, lemmas, kept_words


FUNCTION_WORDS, GRAMMATICAL_CATEGORIES, FUNCTION_LEMMAS, KEPT_WORDS = _load_function_words()
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


@dataclass
class TextStats:
    word_count: int = 0
    unique_word_count: int = 0
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
    pos_verb_ratio: float | None = None
    pos_adjective_ratio: float | None = None
    pos_adverb_ratio: float | None = None
    flesch: float = 0

    def to_dict(self): return asdict(self)


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


def _punctuation_diversity(text: str) -> float:
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


def compute_stats(text: str) -> TextStats:
    words, sentences = tokenize(text), split_sentences(text)
    repetition_words = tokenize_repetitions(text)
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
    noun_ratio, verb_ratio, adjective_ratio, adverb_ratio = _grammatical_ratios(words)
    content_lemmas = filtered_lemmas(words)
    structures = sentence_structure_signatures(split_structure_units(text))
    encoded_text = text.encode("utf-8")
    gzip_ratio = len(gzip.compress(encoded_text, mtime=0)) / len(encoded_text) if encoded_text else 0
    syntax = analyze_syntax(text)
    return TextStats(
        word_count=len(words), unique_word_count=len(frequencies), sentence_count=len(lengths),
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
        punctuation_diversity=r(_punctuation_diversity(text)),
        punctuation_per_300_words=r(len(PUNCTUATION_MARK_RE.findall(text)) / len(words) * 300),
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
        pos_verb_ratio=r(syntax["pos_distribution"]["verbs"]) if syntax else None,
        pos_adjective_ratio=r(syntax["pos_distribution"]["adjectives"]) if syntax else None,
        pos_adverb_ratio=r(syntax["pos_distribution"]["adverbs"]) if syntax else None,
        flesch=r(flesch),
    )


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
