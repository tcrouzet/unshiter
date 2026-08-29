"""Profondeur des arbres de dépendances français analysés avec spaCy."""

from functools import lru_cache
from collections import Counter
import re

from .config import (
    COMPARISON_MARKERS_FILE,
    NEGATION_COMPLETE_MARKERS_FILE,
    ABSTRACT_NOUN_SUFFIXES_FILE, CONCRETE_NOUN_EXCEPTIONS_FILE,
    STATIVE_VERBS_FILE, TEMPORAL_CONNECTORS_FILE,
    MODAL_VERBS_FILE,
    SPACY_FRENCH_MODEL,
    SPACY_RELATIVE_DEPENDENCIES,
    SPACY_SUBORDINATE_DEPENDENCIES,
)

NOMINAL_MODIFIER_DEPS = {"amod", "nmod", "acl:relcl", "acl"}
ALWAYS_PERSONAL_PRONOUNS = {"je", "j", "tu", "nous", "vous", "elle", "elles", "ils"}
IMPERSONAL_IL_VERBS = {"pleuvoir", "neiger", "falloir", "sembler", "arriver", "suffire", "convenir", "s'agir"}
GENERIC_SUBJECT_PRONOUNS = {"on", "chacun", "quiconque", "nul", "tout", "certains", "beaucoup"}


@lru_cache(maxsize=1)
def _load_modal_verbs() -> set[str]:
    if not MODAL_VERBS_FILE.exists():
        return set()
    result = set()
    for line in MODAL_VERBS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip().casefold()
        if ":" in line:
            line = line.rsplit(":", 1)[1].strip()
        if line:
            result.add(line)
    return result


def modal_generalization_ratio(doc, generic_subjects: set[str] | None = None) -> float:
    """Part des verbes modaux dont le sujet est générique ou impersonnel."""
    verbs = [token for token in doc if token.pos_ in {"VERB", "AUX"}]
    if not verbs:
        return 0.0
    generic = set(generic_subjects or GENERIC_SUBJECT_PRONOUNS) | {"on"}
    modals = _load_modal_verbs()
    count = 0
    for verb in verbs:
        if verb.lemma_.casefold() not in modals:
            continue
        subjects = [child for child in verb.children if child.dep_ in {"nsubj", "nsubj:pass"}]
        if verb.lemma_.casefold() == "falloir" or any(subject.lower_ in generic for subject in subjects):
            count += 1
    return count / len(verbs)


def _is_personal_subject(token) -> bool | None:
    if token.dep_ not in {"nsubj", "nsubj:pass"}: return None
    if token.pos_ == "PROPN": return True
    if token.pos_ != "PRON": return None
    word = token.lower_
    if word in ALWAYS_PERSONAL_PRONOUNS: return True
    if word == "il":
        if token.head.lemma_ in IMPERSONAL_IL_VERBS: return False
        if token.head.lemma_ == "avoir" and any(c.lower_ == "y" for c in token.head.children): return False
        return True
    return None


def _is_generic_subject(token) -> bool:
    return token.pos_ == "NOUN" or (token.pos_ == "PRON" and token.lower_ in GENERIC_SUBJECT_PRONOUNS)


def _is_gnomic_present_verb(token, is_dialogue: bool = False) -> bool:
    if is_dialogue or "Fin" not in token.morph.get("VerbForm") or "Pres" not in token.morph.get("Tense") or "Ind" not in token.morph.get("Mood"):
        return False
    return any(_is_generic_subject(child) for child in token.children if child.dep_ in {"nsubj", "nsubj:pass"})

EXCLAMATIVE_OPENERS = {"que", "comme", "quel", "quelle", "quels", "quelles"}

def _is_exclamative_sentence(sentence) -> bool:
    tokens = list(sentence)
    return bool(tokens and sentence.text.strip().endswith("!") and tokens[0].lower_ in EXCLAMATIVE_OPENERS)


def incise_density(doc) -> float:
    """Part des phrases contenant une incise repérée dans l'arbre syntaxique."""
    sentences = list(doc.sents)
    if not sentences:
        return 0.0
    count = 0
    for sentence in sentences:
        for token in sentence:
            if token.dep_ not in {"appos", "acl:relcl", "advcl", "parataxis"} or token.i <= sentence.start:
                continue
            before = doc[token.i - 1] if token.i > 0 else None
            if before is not None and before.text == ",":
                count += 1
                break
    return count / len(sentences)


def coordination_accumulation_ratio(doc) -> float:
    """Part des phrases comportant plus de deux coordinations syntaxiques."""
    sentences = list(doc.sents)
    if not sentences:
        return 0.0
    return sum(sum(token.dep_ == "cc" for token in sentence) > 2 for sentence in sentences) / len(sentences)


def _max_depth_from_last_token(sentence) -> int:
    tokens = [token for token in sentence if not token.is_punct]
    if not tokens:
        return 0
    last = tokens[-1]
    depth = 0
    node = last
    while node.head != node and node.head.i >= sentence.start:
        depth += 1
        node = node.head
    return depth


def right_branching_depth(doc) -> float:
    """Profondeur moyenne de la chaîne de dépendances du dernier mot."""
    sentences = list(doc.sents)
    if not sentences:
        return 0.0
    return sum(_max_depth_from_last_token(sentence) for sentence in sentences) / len(sentences)


def _noun_modifier_counts(doc) -> list[int]:
    return [sum(child.dep_ in NOMINAL_MODIFIER_DEPS for child in token.children)
            for token in doc if token.pos_ in {"NOUN", "PROPN"}]


def _coordinated_modifier_chains(doc) -> list[int]:
    chains = []
    for token in doc:
        if token.pos_ == "ADJ" and token.dep_ == "amod":
            chain = [token] + [child for child in token.children if child.dep_ == "conj" and child.pos_ == "ADJ"]
            if len(chain) > 1:
                chains.append(len(chain))
    return chains


def proper_noun_density(doc) -> float:
    """Part des tokens lexicaux étiquetés PROPN par spaCy."""
    tokens = [token for token in doc if not token.is_space and not token.is_punct]
    return sum(token.pos_ == "PROPN" for token in tokens) / len(tokens) if tokens else 0.0


def _load_word_list(path):
    try:
        return {(line.split(":", 1)[-1]).strip().casefold() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")}
    except OSError:
        return set()


ABSTRACT_SUFFIXES = tuple(_load_word_list(ABSTRACT_NOUN_SUFFIXES_FILE))
CONCRETE_EXCEPTIONS = _load_word_list(CONCRETE_NOUN_EXCEPTIONS_FILE)


def _is_abstract_noun(lemma: str) -> bool:
    return lemma.casefold() not in CONCRETE_EXCEPTIONS and lemma.casefold().endswith(ABSTRACT_SUFFIXES)


def concrete_noun_ratio(doc) -> float:
    nouns = [token for token in doc if token.pos_ == "NOUN"]
    return sum(not _is_abstract_noun(token.lemma_) for token in nouns) / len(nouns) if nouns else 0.0


def tense_shift_rate(paragraphs: list[str], nlp) -> float:
    """Part des changements de temps dominant entre paragraphes successifs."""
    dominant = []
    for paragraph in paragraphs:
        tenses = [token.morph.get("Tense")[0] for token in nlp(paragraph)
                  if token.pos_ == "VERB" and token.morph.get("Tense")]
        if tenses:
            dominant.append(Counter(tenses).most_common(1)[0][0])
    if len(dominant) < 2:
        return 0.0
    return sum(a != b for a, b in zip(dominant, dominant[1:])) / (len(dominant) - 1)


def _tense_shift_rate_doc(text: str, doc) -> float:
    """Même mesure à partir du Doc déjà analysé, sans second appel spaCy."""
    ranges, offset = [], 0
    for paragraph in re.split(r"\n\s*\n+", text):
        if paragraph.strip(): ranges.append((offset, offset + len(paragraph)))
        offset += len(paragraph) + 1
    dominant = []
    for start, end in ranges:
        tenses = [token.morph.get("Tense")[0] for token in doc
                  if start <= token.idx < end and token.pos_ == "VERB" and token.morph.get("Tense")]
        if tenses: dominant.append(Counter(tenses).most_common(1)[0][0])
    return sum(a != b for a, b in zip(dominant, dominant[1:])) / (len(dominant) - 1) if len(dominant) > 1 else 0.0


DIALOGUE_OPENING_MARKERS = ("—", "–", "«")  # cadratin, demi-cadratin ou guillemet
WORD_RE = re.compile(r"[\wÀ-ÖØ-öø-ÿ]+(?:['’][\wÀ-ÖØ-öø-ÿ]+)?", re.UNICODE)


def dialogue_char_ranges(text: str) -> list[tuple[int, int]]:
    ranges, offset = [], 0
    for paragraph in re.split(r"(\n\s*\n)", text):
        start, end = offset, offset + len(paragraph)
        offset = end
        if paragraph.strip().startswith(DIALOGUE_OPENING_MARKERS):
            ranges.append((start, end))
    # Les répliques peuvent aussi être enchâssées dans un paragraphe narratif
    # (« Mais pourquoi tu m'as appelé ? »). Elles doivent être exclues des
    # mesures narratives même si le paragraphe ne commence pas par un guillemet.
    ranges.extend((match.start(), match.end()) for match in re.finditer(r"«[^»]*»", text, re.DOTALL))
    ranges.sort()
    merged = []
    for start, end in ranges:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _in_dialogue(char_index: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= char_index < end for start, end in ranges)


def _sentence_in_dialogue(sentence, ranges: list[tuple[int, int]]) -> bool:
    """Vrai si la phrase chevauche un segment dialogué."""
    return any(sentence.start_char < end and sentence.end_char > start for start, end in ranges)

NEGATION_MARKERS = {"pas", "plus", "jamais", "rien", "personne", "aucun", "aucune", "guère", "nulle"}


@lru_cache(maxsize=1)
def _negation_complete_markers() -> frozenset[str]:
    try:
        return frozenset(line.strip().casefold() for line in NEGATION_COMPLETE_MARKERS_FILE.read_text(encoding="utf-8").splitlines()
                         if line.strip() and not line.lstrip().startswith("#"))
    except OSError:
        return frozenset({"pas", "plus", "jamais", "guère"})


def _is_simple_past(token) -> bool:
    grammatical = (token.pos_ in {"VERB", "AUX"} and "Fin" in token.morph.get("VerbForm")
                   and "Past" in token.morph.get("Tense") and "Ind" in token.morph.get("Mood"))
    # Certains modèles spaCy classent les formes littéraires en participe ;
    # ce secours morphographique ne s'applique qu'à une forme verbale isolée.
    # Le grand modèle confond parfois les troisièmes personnes en -a avec un
    # participe passé ; on ne retient ce secours que lorsque son propre tag
    # indique déjà le passé et la forme verbale.
    endings = ("a", "it", "ut", "îmes", "îtes", "irent", "urent", "ûmes", "ûtes")
    orthographic = token.text.lower().endswith(endings) and token.text.lower() != "a"
    grammatical = grammatical and orthographic
    fallback = (token.pos_ == "VERB" and token.text.lower().endswith("a")
                and "Past" in token.morph.get("Tense")
                and "Part" in token.morph.get("VerbForm"))
    return (grammatical or fallback) and not any(child.dep_ in {"aux", "aux:pass"} for child in token.children)


def _is_literary_subjunctive(token) -> bool:
    grammatical = (token.pos_ in {"VERB", "AUX"} and "Fin" in token.morph.get("VerbForm")
                   and "Sub" in token.morph.get("Mood") and "Imp" in token.morph.get("Tense"))
    fallback = token.text.lower().endswith(("ât", "assent", "ussions", "ussiez", "û t".replace(" ", ""), "ûtes", "ussent"))
    return grammatical or fallback


def _is_ne_marker(token) -> bool:
    # spaCy conserve parfois l’apostrophe typographique dans les contractions
    # (« n’écrirai ») et parfois la sépare du pronom. On normalise les deux.
    normalized = token.text.lower().replace("’", "'")
    return normalized in {"ne", "n'"} or (normalized == "n" and token.text.endswith(("'", "’")))


def sentence_negation_stats(sentence) -> tuple[int, int]:
    """Retourne (négations, négations précédées de « ne »)."""
    tokens = list(sentence)
    total = with_ne = 0
    for index, token in enumerate(tokens):
        if not _is_negation_marker(tokens, index):
            continue
        total += 1
        context = tokens[max(0, index - 8):min(len(tokens), index + 9)]
        if any(_is_ne_marker(previous) for previous in context if previous is not token):
            with_ne += 1
    return total, with_ne


def sentence_paired_negation_stats(sentence) -> tuple[int, int]:
    """Compte seulement les marqueurs pouvant former une négation avec « ne »."""
    tokens = list(sentence)
    candidates = _negation_complete_markers()
    total = with_ne = 0
    for index, token in enumerate(tokens):
        if token.lower_ not in candidates or not _is_negation_marker(tokens, index):
            continue
        previous_word = tokens[index - 1].lower_ if index else ""
        if token.lower_ == "pas" and (previous_word.isdigit() or previous_word in {"deux", "trois", "à", "a"}):
            continue
        # Une ellipse nominale/adjectivale (« pas besoin », « pas rassurant »)
        # n'est pas une négation verbale dont le « ne » serait omis.
        if (token.dep_ not in {"advmod", "neg"}
                or token.head.pos_ not in {"VERB", "AUX"}
                or "Fin" not in token.head.morph.get("VerbForm")):
            continue
        total += 1
        context = tokens[max(0, index - 8):min(len(tokens), index + 9)]
        if any(_is_ne_marker(other) for other in context if other is not token):
            with_ne += 1
    return total, with_ne


def _is_negation_marker(tokens, index: int) -> bool:
    """Évite les homonymes non négatifs ("plus chaud", "de plus", etc.)."""
    token = tokens[index]
    word = token.lower_
    if word not in NEGATION_MARKERS:
        return False
    if word != "plus":
        return True
    previous = tokens[index - 1].lower_ if index else ""
    following = tokens[index + 1].lower_ if index + 1 < len(tokens) else ""
    before = {t.lower_ for t in tokens[max(0, index - 8):index]}
    if "ne" in before or "n'" in before or "n’" in before:
        return True
    if following in {"aucun", "aucune", "personne", "rien", "jamais", "guère"}:
        return True
    if previous in {"de", "en", "et", "ou", "a", "à", "au", "aux"}:
        return False
    if following in {"que", "qu'", "qu’"}:
        return False
    # Comparatif/adverbe d'intensité (« plus chaud », « plus vite »).
    return False


def _is_periphrastic_future(token) -> bool:
    return (token.lemma_ == "aller" and token.pos_ in {"VERB", "AUX"}
            and "Fin" in token.morph.get("VerbForm") and "Pres" in token.morph.get("Tense")
            and "Ind" in token.morph.get("Mood") and any(
                child.pos_ == "VERB" and "Inf" in child.morph.get("VerbForm")
                and child.dep_ in {"xcomp", "ccomp"} for child in token.children))


def _is_simple_future(token) -> bool:
    return (token.pos_ in {"VERB", "AUX"} and "Fin" in token.morph.get("VerbForm")
            and "Fut" in token.morph.get("Tense") and "Ind" in token.morph.get("Mood"))


def _comparison_markers() -> tuple[str, ...]:
    return tuple(
        line.strip().lower().replace("’", "'")
        for line in COMPARISON_MARKERS_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


@lru_cache(maxsize=1)
def _pipeline():
    try:
        import spacy
        return spacy.load(SPACY_FRENCH_MODEL, disable=["ner"])
    except (ImportError, OSError):
        return None


def _token_depth(token) -> int:
    depth = 0
    current = token
    seen = {token.i}
    while current.head.i != current.i and current.head.i not in seen:
        current = current.head
        seen.add(current.i)
        depth += 1
    return depth


def _is_clause_predicate(token) -> bool:
    """Repère les noyaux verbaux, y compris les temps composés."""
    if token.pos_ == "VERB":
        return "Fin" in token.morph.get("VerbForm") or any(
            child.pos_ == "AUX" and "Fin" in child.morph.get("VerbForm")
            for child in token.children
        )
    return (
        token.pos_ == "AUX"
        and "Fin" in token.morph.get("VerbForm")
        and token.dep_ in {"ROOT", "conj", "advcl", "ccomp", "xcomp", "acl", "acl:relcl"}
    )


def _is_passive_predicate(token) -> bool:
    return (
        "Pass" in token.morph.get("Voice")
        or any(child.dep_ == "aux:pass" for child in token.children)
        or any(child.dep_ == "nsubj:pass" for child in token.children)
    )


def _comme_is_circumstantial(token) -> bool:
    """Distingue une proposition introduite par « comme » d'une comparaison."""
    head = token.head
    return (
        head.pos_ in {"VERB", "AUX"}
        and head.dep_ == "advcl"
        and head.i < head.head.i
    )


def _contains_comparison(sentence) -> bool:
    if any(token.lower_ == "comme" and not _comme_is_circumstantial(token) for token in sentence):
        return True
    normalized = re.sub(r"\s+", " ", sentence.text.lower().replace("’", "'")).strip()
    return any(marker in normalized for marker in _comparison_markers())


def analyze_syntax(text: str, doc=None) -> dict[str, object] | None:
    """Profondeur, propositions dépendantes et répartition grammaticale."""
    if doc is None:
        nlp = _pipeline()
        if nlp is None:
            return None
        if len(text) > nlp.max_length:
            nlp.max_length = len(text) + 1
        doc = nlp(text)
    paragraphs = [part for part in re.split(r"\n\s*\n+", text) if part.strip()]
    sentences = list(doc.sents)
    dialogue_ranges = dialogue_char_ranges(text)
    narrative_sentences = [sentence for sentence in sentences if not _sentence_in_dialogue(sentence, dialogue_ranges)]
    narrative_tokens = [token for sentence in narrative_sentences for token in sentence]
    depths = [max((_token_depth(token) for token in sentence if not token.is_punct), default=0) for sentence in sentences]
    nominal_sentences = sum(
        not any(token.pos_ in {"VERB", "AUX"} and "Fin" in token.morph.get("VerbForm") for token in sentence)
        for sentence in sentences
    )
    relative_clauses = sum(token.dep_ in SPACY_RELATIVE_DEPENDENCIES for token in doc)
    subordinate_clauses = sum(token.dep_ in SPACY_SUBORDINATE_DEPENDENCIES for token in doc)
    sentence_predicates = [[token for token in sentence if _is_clause_predicate(token)] for sentence in narrative_sentences]
    active_sentences = sum(
        bool(predicates) and not any(_is_passive_predicate(token) for token in predicates)
        for predicates in sentence_predicates
    )
    comparison_sentences = sum(_contains_comparison(sentence) for sentence in sentences)
    finite_verbs = sum(token.pos_ in {"VERB", "AUX"} and "Fin" in token.morph.get("VerbForm") for token in narrative_tokens)
    present_participles = sum(token.pos_ in {"VERB", "AUX"} and "Part" in token.morph.get("VerbForm") and "Pres" in token.morph.get("Tense") for token in doc)
    past_participles = sum(token.pos_ in {"VERB", "AUX"} and "Part" in token.morph.get("VerbForm") and "Past" in token.morph.get("Tense") for token in doc)
    # Les formes en -it sont parfois homographes du présent (retentit,
    # adoucit). On les retient seulement si la phrase fournit un contexte
    # passé ; une phrase entièrement au présent ne doit pas produire de faux
    # passé simple.
    def reliable_simple_past(sentence):
        candidates = [token for token in sentence if _is_simple_past(token)]
        if not candidates:
            return []
        finite = [token for token in sentence if token.pos_ in {"VERB", "AUX"} and "Fin" in token.morph.get("VerbForm")]
        has_other_past = any(token not in candidates and "Past" in token.morph.get("Tense") for token in finite)
        has_present = any("Pres" in token.morph.get("Tense") for token in finite)
        return [] if has_present and not has_other_past else candidates
    simple_past_tokens = [token for sentence in narrative_sentences for token in reliable_simple_past(sentence)]
    simple_past = len(simple_past_tokens)
    literary_subjunctive = sum(_is_literary_subjunctive(token) for token in narrative_tokens)
    # Le modèle peut étiqueter une forme littéraire comme NOUN/Part : elle
    # reste néanmoins un verbe fini pour les ratios de temps.
    finite_verbs += sum(1 for token in narrative_tokens if (_is_simple_past(token) or _is_literary_subjunctive(token)) and not (token.pos_ in {"VERB", "AUX"} and "Fin" in token.morph.get("VerbForm")))
    negation_totals = [sentence_negation_stats(sentence) for sentence in narrative_sentences]
    paired_negations = [sentence_paired_negation_stats(sentence) for sentence in narrative_sentences]
    negation_total = sum(total for total, _with_ne in paired_negations)
    negation_with_ne = sum(with_ne for _total, with_ne in paired_negations)
    all_negation_totals = [sentence_negation_stats(sentence) for sentence in sentences]
    negation_sentence_ratio = (sum(total > 0 for total, _with_ne in all_negation_totals) / len(sentences)
                               if sentences else 0)
    periphrastic_future = sum(_is_periphrastic_future(token) for token in narrative_tokens)
    simple_future = sum(_is_simple_future(token) for token in narrative_tokens)
    future_total = periphrastic_future + simple_future
    pos_counts = {
        "common_nouns": sum(token.pos_ == "NOUN" for token in doc),
        "proper_nouns": sum(token.pos_ == "PROPN" for token in doc),
        "verbs": finite_verbs,
        "adjectives": sum(token.pos_ == "ADJ" for token in doc),
        "adverbs": sum(token.pos_ == "ADV" for token in doc),
    }
    pos_total = sum(pos_counts.values())
    pos_distribution = {name: count / pos_total if pos_total else 0 for name, count in pos_counts.items()}
    modifier_counts = _noun_modifier_counts(doc)
    adjective_chains = _coordinated_modifier_chains(doc)
    stative = _load_word_list(STATIVE_VERBS_FILE)
    finite_narrative = [t for t in narrative_tokens if t.pos_ in {"VERB", "AUX"} and "Fin" in t.morph.get("VerbForm")]
    action_verb_ratio = sum((t.lemma_.casefold() not in stative) for t in finite_narrative) / len(finite_narrative) if finite_narrative else 0
    subjects = [_is_personal_subject(t) for t in doc if t.dep_ in {"nsubj", "nsubj:pass"}]
    decided_subjects = [x for x in subjects if x is not None]
    personal_subject_ratio = sum(decided_subjects) / len(decided_subjects) if decided_subjects else 0
    narrative_past_ratio = sum("Past" in t.morph.get("Tense") for t in finite_narrative) / len(finite_narrative) if finite_narrative else 0
    gnomic_present_count = sum(_is_gnomic_present_verb(token) for token in narrative_tokens)
    gnomic_present_ratio = gnomic_present_count / len(finite_narrative) if finite_narrative else 0
    return {
        "average_depth": sum(depths) / len(depths) if depths else 0,
        "sentence_count": len(depths),
        "relative_clauses": relative_clauses,
        "subordinate_clauses": subordinate_clauses,
        "relative_clause_ratio": relative_clauses / len(depths) if depths else 0,
        "subordinate_clause_ratio": subordinate_clauses / len(depths) if depths else 0,
        "nominal_sentence_count": nominal_sentences,
        "nominal_sentence_ratio": nominal_sentences / len(depths) if depths else 0,
        "active_voice_ratio": active_sentences / len(sentences) if sentences else None,
        "metaphorical_comme_ratio": comparison_sentences / len(sentences) if sentences else None,
        "pos_distribution": pos_distribution,
        "proper_noun_density": proper_noun_density(doc),
        "concrete_noun_ratio": concrete_noun_ratio(doc),
        "tense_shift_rate": _tense_shift_rate_doc(text, doc),
        "finite_verbs": finite_verbs,
        "present_participles": present_participles,
        "past_participles": past_participles,
        "simple_past": simple_past,
        "literary_subjunctive": literary_subjunctive,
        "literary_tense_ratio": (simple_past + literary_subjunctive) / finite_verbs if finite_verbs else 0,
        "negation_total": negation_total,
        "negation_with_ne": negation_with_ne,
        "negation_completeness_ratio": negation_with_ne / negation_total if negation_total else None,
        "negation_ratio": negation_sentence_ratio,
        "periphrastic_future": periphrastic_future,
        "simple_future": simple_future,
        "future_total": future_total,
        "periphrastic_future_ratio": periphrastic_future / future_total if future_total else None,
        "dialogue_ratio": sum(len(WORD_RE.findall(text[start:end])) for start, end in dialogue_ranges) / len(WORD_RE.findall(text)) if WORD_RE.findall(text) else 0,
        "avg_modifiers_per_noun": sum(modifier_counts) / len(modifier_counts) if modifier_counts else 0,
        "heavily_modified_noun_ratio": sum(c >= 2 for c in modifier_counts) / len(modifier_counts) if modifier_counts else 0,
        "adjective_chain_ratio": len(adjective_chains) / len(sentences) if sentences else 0,
        "avg_adjective_chain_length": sum(adjective_chains) / len(adjective_chains) if adjective_chains else 0,
        "action_verb_ratio": action_verb_ratio,
        "personal_subject_ratio": personal_subject_ratio,
        "narrative_past_ratio": narrative_past_ratio,
        "gnomic_present_ratio": gnomic_present_ratio,
        "exclamative_construction_ratio": sum(_is_exclamative_sentence(s) for s in sentences) / len(sentences) if sentences else 0,
        "incise_density": incise_density(doc),
        "coordination_accumulation_ratio": coordination_accumulation_ratio(doc),
        "right_branching_depth": right_branching_depth(doc),
        "modal_generalization_ratio": modal_generalization_ratio(doc),
    }


def analyze_contextual_tokens(text: str, doc=None) -> list[tuple[str, str, str, int, int]] | None:
    """Graphie, lemme, catégorie française et offsets issus du contexte spaCy."""
    if doc is None:
        nlp = _pipeline()
        if nlp is None:
            return None
        if len(text) > nlp.max_length:
            nlp.max_length = len(text) + 1
        doc = nlp(text)
    categories = {
        "ADP": "préposition", "CCONJ": "conjonction", "DET": "déterminant",
        "INTJ": "interjection", "PRON": "pronom", "SCONJ": "conjonction",
        "AUX": "verbe", "VERB": "verbe", "NOUN": "nom", "PROPN": "nom propre",
        "ADJ": "adjectif", "ADV": "adverbe",
    }
    result = []
    for token in doc:
        if not token.is_alpha:
            continue
        word = token.text.lower()
        lemma = token.lemma_.lower() or word
        category = categories.get(token.pos_, token.pos_.lower())
        # Deux copules successives rattachées au même attribut signalent que
        # la première forme a été nominalisée à tort par le parseur.
        following = doc[token.i + 1] if token.i + 1 < len(doc) else None
        if token.dep_ == "cop" and following is not None and following.dep_ == "cop" and token.head == following.head:
            lemma, category = word, "nom"
        result.append((word, lemma, category, token.idx, token.idx + len(token.text)))
    return result


def average_dependency_depth(text: str) -> float | None:
    analysis = analyze_syntax(text)
    return analysis["average_depth"] if analysis else None
