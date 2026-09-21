"""
Découpage d'un texte Markdown en blocs, puis des blocs en phrases.

Le découpage en BLOCS (paragraphes, titres, listes, citations, code...)
reste une logique maison volontairement simple : le but n'est pas de
réécrire un parseur Markdown complet, juste de repérer les zones de
texte "normal" où la notion de "phrase" a un sens, et de laisser de
côté ce qui n'en a pas (blocs de code, séparateurs, lignes vides).

Le découpage d'un bloc en PHRASES, lui, peut se faire de deux façons au
choix (voir config.SENTENCE_SPLIT_MODE) :
  - "spacy" : segmentation via spaCy (modèle français, nlp_loader.py),
    plus robuste sur les cas piégeux (guillemets, dialogue...).
  - "regex" : un regex maison, zéro dépendance.
Ce choix est entièrement interne à ce module : le reste du pipeline
(burst_detect.py, render_html.py...) appelle juste split_sentences_batch()
sans jamais savoir laquelle des deux méthodes est utilisée.
"""

import re
from dataclasses import dataclass, field

from . import config

_HEADING_RE = re.compile(r'^\s{0,3}#{1,6}\s')
_LIST_ITEM_RE = re.compile(r'^\s*([-*+]|\d+[.)])\s+')
_BLOCKQUOTE_RE = re.compile(r'^\s*>\s?')
_CODE_FENCE_RE = re.compile(r'^\s*(```|~~~)')
_HR_RE = re.compile(r'^\s*([-*_]\s*){3,}$')


@dataclass
class Block:
    kind: str          # "paragraph" | "heading" | "list_item" | "blockquote" | "code" | "other"
    text: str          # contenu textuel analysable (sans le marqueur "- " ou "> ")
    prefix: str = ""   # marqueur à réinjecter tel quel lors de la reconstruction
    raw: str = ""       # ligne(s) brute(s) d'origine (pour les blocs non analysés)


# --- Mode "regex" : zéro dépendance ------------------------------------
#
# Une phrase se termine par "..." (points de suspension tapés), par le
# caractère … , ou par un simple . ! ? — éventuellement suivi d'un espace
# typographique puis d'une fermeture de guillemet/parenthèse (le français
# met une espace AVANT le guillemet fermant : "? ») et/ou d'un marqueur
# Markdown fermant (*, **, _, `) resté sur le texte source (ex :
# "*Six heures.*"). Ce groupe entier ("end") reste attaché à la phrase
# qui précède ; seul l'espace qui suit, avant le début de la phrase
# suivante (majuscule, chiffre, guillemet ouvrant, ou marqueur Markdown
# ouvrant), sert de séparateur et disparaît.
_SENTENCE_BOUNDARY_RE = re.compile(
    r'(?P<end>(?:\.\.\.|[.!?…])(?:\s?[»”"\')*_`]+)?)\s+(?=[*_`]*[A-ZÀ-ÖØ-Þ0-9«"“(\-])'
)


def _split_sentences_regex(text: str):
    text = text.strip()
    if not text:
        return []

    sentences = []
    last = 0
    for m in _SENTENCE_BOUNDARY_RE.finditer(text):
        end_pos = m.start() + len(m.group("end"))
        sentence = text[last:end_pos].strip()
        if sentence:
            sentences.append(sentence)
        last = m.end()

    tail = text[last:].strip()
    if tail:
        sentences.append(tail)

    return sentences


def _split_sentences_batch_regex(texts):
    return [_split_sentences_regex(t) for t in texts]


# --- Mode "spacy" : nécessite spaCy + le modèle français ---------------


def _split_sentences_batch_spacy(texts):
    # Import local : pour que le mode "regex" fonctionne même si spaCy
    # n'est pas installé (le module nlp_loader n'est chargé qu'ici).
    from . import nlp_loader

    results = [[] for _ in texts]
    indexed = [(i, t.strip()) for i, t in enumerate(texts) if t.strip()]
    if not indexed:
        return results

    nlp = nlp_loader.get_nlp()
    docs = nlp.pipe(t for _, t in indexed)
    for (i, _), doc in zip(indexed, docs):
        results[i] = [s.text.strip() for s in doc.sents if s.text.strip()]
    return results


# --- Dispatch, piloté par config.SENTENCE_SPLIT_MODE --------------------


def split_sentences_batch(texts, mode: str = None):
    """Découpe PLUSIEURS textes en phrases en un seul passage (plus rapide
    qu'appeler `split_sentences()` texte par texte sur un document entier).

    Retourne une liste de listes (une par texte d'entrée, même ordre). La
    méthode utilisée (spaCy ou regex) vient de config.SENTENCE_SPLIT_MODE,
    sauf si `mode` est explicitement fourni.
    """
    mode = mode or config.SENTENCE_SPLIT_MODE
    if mode == "regex":
        return _split_sentences_batch_regex(texts)
    if mode == "spacy":
        return _split_sentences_batch_spacy(texts)
    raise ValueError(f"Mode de découpage de phrases inconnu : {mode!r} (attendu: 'spacy' ou 'regex')")


def split_sentences(text: str, mode: str = None):
    """Découpe un seul texte en phrases. Pratique pour un usage isolé
    (tests, script ponctuel) ; pour un document entier, préférer
    `split_sentences_batch` pour la performance."""
    return split_sentences_batch([text], mode=mode)[0]


def iter_blocks(md_text: str):
    """Découpe un document Markdown en blocs analysables.

    Chaque bloc est soit :
      - "paragraph" / "list_item" / "blockquote" / "heading" : du texte
        sur lequel on applique la détection de burstiness ;
      - "code" / "other" : passé tel quel, jamais modifié.
    Les lignes vides séparent les blocs mais sont ré-émises comme des
    blocs "other" pour préserver la mise en page d'origine.
    """
    lines = md_text.splitlines()
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]

        if _CODE_FENCE_RE.match(line):
            fence = line.strip()[:3]
            block_lines = [line]
            i += 1
            while i < n and not lines[i].strip().startswith(fence):
                block_lines.append(lines[i])
                i += 1
            if i < n:
                block_lines.append(lines[i])
                i += 1
            yield Block(kind="code", text="", raw="\n".join(block_lines))
            continue

        if not line.strip():
            yield Block(kind="other", text="", raw=line)
            i += 1
            continue

        if _HR_RE.match(line):
            yield Block(kind="other", text="", raw=line)
            i += 1
            continue

        if _HEADING_RE.match(line):
            marker = _HEADING_RE.match(line).group(0)
            yield Block(kind="heading", text=line[len(marker):], prefix=marker)
            i += 1
            continue

        m_list = _LIST_ITEM_RE.match(line)
        if m_list:
            marker = m_list.group(0)
            content_lines = [line[len(marker):]]
            i += 1
            # continuation lines of the same list item (indented, non-blank,
            # not starting a new list item / heading / blockquote)
            while (
                i < n
                and lines[i].strip()
                and not _LIST_ITEM_RE.match(lines[i])
                and not _HEADING_RE.match(lines[i])
                and not _BLOCKQUOTE_RE.match(lines[i])
                and not _CODE_FENCE_RE.match(lines[i])
            ):
                content_lines.append(lines[i].strip())
                i += 1
            yield Block(kind="list_item", text=" ".join(content_lines), prefix=marker)
            continue

        m_bq = _BLOCKQUOTE_RE.match(line)
        if m_bq:
            marker = m_bq.group(0)
            content_lines = [line[len(marker):]]
            i += 1
            while i < n and _BLOCKQUOTE_RE.match(lines[i]):
                content_lines.append(_BLOCKQUOTE_RE.match(lines[i]).expand(r'') or lines[i])
                content_lines[-1] = _BLOCKQUOTE_RE.sub('', lines[i], count=1)
                i += 1
            yield Block(kind="blockquote", text=" ".join(content_lines), prefix=marker)
            continue

        # paragraphe : on accumule les lignes jusqu'à une ligne vide ou un
        # nouveau type de bloc
        content_lines = [line]
        i += 1
        while (
            i < n
            and lines[i].strip()
            and not _HEADING_RE.match(lines[i])
            and not _LIST_ITEM_RE.match(lines[i])
            and not _BLOCKQUOTE_RE.match(lines[i])
            and not _CODE_FENCE_RE.match(lines[i])
            and not _HR_RE.match(lines[i])
        ):
            content_lines.append(lines[i])
            i += 1
        yield Block(kind="paragraph", text=" ".join(content_lines))
