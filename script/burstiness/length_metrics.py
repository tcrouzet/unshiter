"""
Choix de l'unité de mesure de la longueur d'une phrase.

Deux modes disponibles (voir config.LENGTH_MODE) :
  - "syllables" : nombre de syllabes (heuristique française, voir
    syllables_fr.py). Plus fin, mais approximatif : peut se tromper sur
    certains mots, ce qui rend la détection de burstiness moins fiable.
  - "words"     : nombre de mots. Plus grossier, mais beaucoup plus
    simple et fiable, aucune heuristique linguistique nécessaire.
"""

import re

from . import config
from . import syllables_fr

# Le trait d'union fait partie du mot : "après-midi", "dix-huit",
# "beau-père" comptent chacun pour UN seul mot, pas deux.
_WORD_RE = re.compile(r"[a-zàâäéèêëîïôöùûüÿœæ]+(?:['’-][a-zàâäéèêëîïôöùûüÿœæ]+)*", re.IGNORECASE)


def count_words(text: str) -> int:
    return len(_WORD_RE.findall(text))


def count_length(text: str, mode: str = None) -> int:
    """Longueur d'une phrase selon le mode choisi (config.LENGTH_MODE par
    défaut, ou surchargé via l'argument `mode`)."""
    mode = mode or config.LENGTH_MODE
    if mode == "words":
        return count_words(text)
    if mode == "syllables":
        return syllables_fr.count_syllables_text(text)
    raise ValueError(f"Mode de longueur inconnu : {mode!r} (attendu: 'syllables' ou 'words')")


def unit_label(mode: str = None) -> str:
    """Libellé pour l'affichage (tooltips, bandeau d'info)."""
    mode = mode or config.LENGTH_MODE
    return "mots" if mode == "words" else "syllabes"
