"""
Couleur d'une phrase surlignée, choisie dans une palette fixe
(config.COLOR_SCALE), par ORDRE (rang), jamais par écart pondéré ou par
seuil de tolérance.

Chaque série est traitée entièrement pour elle-même (jamais comparée au
reste du document) :
  1. on relève les longueurs DISTINCTES présentes dans CETTE série ;
  2. celle la plus proche de la médiane de la série -> gris clair ;
  3. les longueurs distinctes strictement supérieures sont triées par
     ordre croissant et reçoivent, dans cet ordre, les couleurs
     suivantes de la palette (vers le rouge) ;
  4. symétriquement, les longueurs distinctes strictement inférieures
     sont triées par ordre décroissant (les plus proches de la médiane
     d'abord) et reçoivent les couleurs précédentes (vers le bleu) ;
  5. au-delà du nombre de couleurs disponibles, la couleur la plus
     extrême de la palette est réutilisée (plafond).

Seul l'ORDRE des longueurs distinctes compte, jamais l'ampleur réelle de
l'écart entre elles.
"""

import statistics
from typing import List

from . import config
from .burst_detect import Run


def series_median(run: Run) -> float:
    """Médiane interne d'une série (sa seule référence)."""
    return statistics.median(run.counts)


def colors_for_run(run: Run) -> List[str]:
    """Couleur de chaque phrase de la série, par rang, sans aucun seuil
    ni pondération — calculée uniquement à partir des longueurs propres
    à cette série."""
    palette = config.COLOR_SCALE
    center = len(palette) // 2

    local_median = series_median(run)
    unique_values = sorted(set(run.counts))

    reference = min(unique_values, key=lambda v: abs(v - local_median))

    above = sorted(v for v in unique_values if v > reference)
    below = sorted((v for v in unique_values if v < reference), reverse=True)

    value_to_color = {reference: palette[center]}
    for rank, value in enumerate(above):
        idx = min(center + 1 + rank, len(palette) - 1)
        value_to_color[value] = palette[idx]
    for rank, value in enumerate(below):
        idx = max(center - 1 - rank, 0)
        value_to_color[value] = palette[idx]

    return [value_to_color[c] for c in run.counts]
