"""
Découpage d'un texte Markdown en blocs, puis des blocs en phrases.

On reste volontairement simple : le but n'est pas de réécrire un parseur
Markdown complet, mais de repérer les zones de texte "normal" (paragraphes,
listes, citations) où la notion de "phrase" a un sens, et de laisser de
côté ce qui n'en a pas (blocs de code, séparateurs, lignes vides).
"""

import re
from dataclasses import dataclass, field

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


def split_sentences(text: str):
    """Découpe une portion de texte "normal" en phrases.

    La ponctuation finale et une éventuelle fermeture de guillemet/
    parenthèse restent attachées à la phrase qui précède ; seul l'espace
    séparateur entre deux phrases est retiré.
    """
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
