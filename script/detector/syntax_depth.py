"""Profondeur des arbres de dépendances français analysés avec spaCy."""

from functools import lru_cache
import re

from .config import (
    COMPARISON_MARKERS_FILE,
    SPACY_FRENCH_MODEL,
    SPACY_RELATIVE_DEPENDENCIES,
    SPACY_SUBORDINATE_DEPENDENCIES,
)


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


def analyze_syntax(text: str) -> dict[str, object] | None:
    """Profondeur, propositions dépendantes et répartition grammaticale."""
    nlp = _pipeline()
    if nlp is None:
        return None
    if len(text) > nlp.max_length:
        nlp.max_length = len(text) + 1
    doc = nlp(text)
    sentences = list(doc.sents)
    depths = [max((_token_depth(token) for token in sentence if not token.is_punct), default=0) for sentence in sentences]
    nominal_sentences = sum(
        not any(token.pos_ in {"VERB", "AUX"} and "Fin" in token.morph.get("VerbForm") for token in sentence)
        for sentence in sentences
    )
    relative_clauses = sum(token.dep_ in SPACY_RELATIVE_DEPENDENCIES for token in doc)
    subordinate_clauses = sum(token.dep_ in SPACY_SUBORDINATE_DEPENDENCIES for token in doc)
    sentence_predicates = [
        [token for token in sentence if _is_clause_predicate(token)]
        for sentence in sentences
    ]
    active_sentences = sum(
        bool(predicates) and not any(_is_passive_predicate(token) for token in predicates)
        for predicates in sentence_predicates
    )
    comparison_sentences = sum(_contains_comparison(sentence) for sentence in sentences)
    pos_counts = {
        "common_nouns": sum(token.pos_ == "NOUN" for token in doc),
        "proper_nouns": sum(token.pos_ == "PROPN" for token in doc),
        "verbs": sum(token.pos_ in {"VERB", "AUX"} for token in doc),
        "adjectives": sum(token.pos_ == "ADJ" for token in doc),
        "adverbs": sum(token.pos_ == "ADV" for token in doc),
    }
    pos_total = sum(pos_counts.values())
    pos_distribution = {name: count / pos_total if pos_total else 0 for name, count in pos_counts.items()}
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
    }


def analyze_contextual_tokens(text: str) -> list[tuple[str, str, str, int, int]] | None:
    """Graphie, lemme, catégorie française et offsets issus du contexte spaCy."""
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
