"""
Détection de la "burstiness" : des suites de phrases consécutives de
longueur similaire (à une tolérance près), en nombre suffisant pour être
stylistiquement notable. La longueur se mesure en syllabes ou en mots,
selon config.LENGTH_MODE (voir length_metrics.py).
"""

from dataclasses import dataclass, field
from typing import List, Tuple

from . import config
from . import length_metrics


@dataclass
class Run:
    start: int          # index (global, toutes phrases confondues) de la 1ère phrase de la série
    end: int            # index exclusif de fin
    length: int         # nombre de phrases dans la série
    reference_count: int  # longueur de la 1ère phrase de la série (référence de tolérance)
    counts: List[int] = field(default_factory=list)  # longueur de chaque phrase de la série

    @property
    def min_count(self) -> int:
        return min(self.counts) if self.counts else self.reference_count

    @property
    def max_count(self) -> int:
        return max(self.counts) if self.counts else self.reference_count


def compute_length_counts(sentences: List[str], mode: str = None) -> List[int]:
    return [length_metrics.count_length(s, mode=mode) for s in sentences]


def _within_tolerance(count: int, reference: int, tolerance: float) -> bool:
    """Deux longueurs sont considérées comme "égales" si leur écart relatif
    à la référence ne dépasse pas `tolerance` (ex: 0.10 = 10 %)."""
    if count == reference:
        return True
    base = max(reference, count, 1)
    return abs(count - reference) <= tolerance * base


def detect_bursts(
    sentences: List[str],
    threshold: int = config.RUN_THRESHOLD,
    tolerance: float = config.LENGTH_TOLERANCE,
    mode: str = None,
) -> Tuple[List[int], List[Run]]:
    """Repère les séries de >= `threshold` phrases consécutives dont la
    longueur (en syllabes ou en mots, voir `mode` / config.LENGTH_MODE)
    reste à +/- `tolerance` de la 1ère phrase de la série (ex :
    tolerance=0.10 -> +/- 10 %).

    Retourne (counts, runs) où `counts[i]` est la longueur de
    `sentences[i]`, et `runs` la liste des séries détectées.
    """
    counts = compute_length_counts(sentences, mode=mode)
    runs: List[Run] = []
    i = 0
    n = len(counts)
    while i < n:
        reference = counts[i]
        j = i + 1
        while j < n and _within_tolerance(counts[j], reference, tolerance):
            j += 1
        run_len = j - i
        if run_len >= threshold:
            runs.append(
                Run(
                    start=i,
                    end=j,
                    length=run_len,
                    reference_count=reference,
                    counts=counts[i:j],
                )
            )
        i = j
    return counts, runs


def run_index_for_sentence(runs: List[Run], sentence_idx: int):
    """Retourne l'indice (dans `runs`) de la série à laquelle appartient la
    phrase `sentence_idx`, ou None si elle n'appartient à aucune série."""
    for k, run in enumerate(runs):
        if run.start <= sentence_idx < run.end:
            return k
    return None
