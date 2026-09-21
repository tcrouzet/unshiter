"""
Détection de la "burstiness" : des suites de phrases consécutives de
longueur similaire (à une tolérance près), en nombre suffisant pour être
stylistiquement notable. La longueur se mesure en syllabes ou en mots,
selon config.LENGTH_MODE (voir length_metrics.py).

Principe : on avance phrase après phrase, comme le ferait un lecteur.
Deux phrases CONSÉCUTIVES sont jugées "proches" si leur écart de longueur
reste sous le seuil de perceptibilité humaine -- pas de médiane de série,
pas de statistique sur tout le document : juste la comparaison de chaque
phrase à sa voisine immédiate. Une série se construit tant que les
phrases restent proches deux à deux ; le premier "trou" (écart trop
grand) la termine.

Le seuil de perceptibilité n'est pas un nombre de mots fixe : il suit la
loi de Weber-Fechner (psychophysique de la perception des quantités) --
la différence perceptible entre deux longueurs croît avec la RACINE
CARRÉE de leur grandeur, pas proportionnellement à elle. Un lecteur
remarque immédiatement 1 mot d'écart entre deux phrases de 3-4 mots, mais
ne remarque pas 4 mots d'écart entre deux phrases de 26-30 mots -- ce qui
est exactement le comportement voulu, et ça se généralise tout seul à un
texte à la Proust (phrases de 60-80 mots) sans aucun réglage manuel en
mots. Voir `_is_close`.
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple

from . import config
from . import length_metrics


@dataclass
class Run:
    start: int          # index (global, toutes phrases confondues) de la 1ère phrase de la série
    end: int            # index exclusif de fin
    length: int         # nombre de phrases dans la série
    reference_count: int  # longueur de la 1ère phrase de la série (info d'affichage)
    counts: List[int] = field(default_factory=list)  # longueur de chaque phrase de la série

    @property
    def min_count(self) -> int:
        return min(self.counts) if self.counts else self.reference_count

    @property
    def max_count(self) -> int:
        return max(self.counts) if self.counts else self.reference_count


def compute_length_counts(sentences: List[str], mode: str = None) -> List[int]:
    return [length_metrics.count_length(s, mode=mode) for s in sentences]


def _is_close(a: int, b: int, k: float) -> bool:
    """Deux longueurs consécutives sont "proches" (indistinguables pour un
    lecteur) si leur écart absolu reste sous `k * sqrt(moyenne(a, b))`
    (loi de Weber-Fechner appliquée à la perception des quantités : le
    seuil de perceptibilité croît avec la racine carrée de la grandeur,
    pas proportionnellement à elle)."""
    if a == b:
        return True
    ref = max((a + b) / 2.0, 1.0)
    margin = k * math.sqrt(ref)
    return abs(a - b) <= margin


def detect_bursts(
    sentences: List[str],
    threshold: int = config.RUN_THRESHOLD,
    k: float = config.LENGTH_TOLERANCE_K,
    mode: str = None,
) -> Tuple[List[int], List[Run]]:
    """Repère les séries de >= `threshold` phrases consécutives dont
    chaque paire de voisines immédiates reste "proche" au sens de
    `_is_close` (longueur en syllabes ou en mots, voir `mode` /
    config.LENGTH_MODE). On avance phrase par phrase ; le premier écart
    trop grand entre deux voisines termine la série en cours.

    Retourne (counts, runs) où `counts[i]` est la longueur de
    `sentences[i]`, et `runs` la liste des séries détectées.
    """
    counts = compute_length_counts(sentences, mode=mode)
    n = len(counts)
    runs: List[Run] = []
    i = 0
    while i < n:
        j = i
        while j + 1 < n and _is_close(counts[j], counts[j + 1], k):
            j += 1
        run_len = j - i + 1
        if run_len >= threshold:
            runs.append(
                Run(
                    start=i,
                    end=j + 1,
                    length=run_len,
                    reference_count=counts[i],
                    counts=counts[i:j + 1],
                )
            )
        i = j + 1
    return counts, runs


def run_index_for_sentence(runs: List[Run], sentence_idx: int):
    """Retourne l'indice (dans `runs`) de la série à laquelle appartient la
    phrase `sentence_idx`, ou None si elle n'appartient à aucune série."""
    for k, run in enumerate(runs):
        if run.start <= sentence_idx < run.end:
            return k
    return None
