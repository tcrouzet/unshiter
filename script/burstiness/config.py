"""
Réglages du détecteur de burstiness.

Modifie ces valeurs pour changer le comportement par défaut du script
(elles peuvent aussi être surchargées en ligne de commande, voir cli.py).
"""

# --- Fichiers ------------------------------------------------------------
#
# Fichier Markdown source à analyser.
SOURCE_FILE = "_wip/source.md"

# Fichier HTML de sortie. Laisser None pour reprendre automatiquement le
# nom du fichier source avec l'extension .html (ex: _wip/source.html).
OUTPUT_FILE = None

# --- Unité de longueur -----------------------------------------------
# Unité utilisée pour mesurer la longueur d'une phrase :
#   "syllables" -> nombre de syllabes (heuristique française, approximative)
#   "words"     -> nombre de mots (plus simple, souvent plus fiable)
# La détection de syllabes en français est une heuristique imparfaite ;
# si elle donne des résultats étranges sur ton texte, passe à "words".
LENGTH_MODE = "words"

# Nombre minimum de phrases consécutives de longueur "similaire" pour
# qu'une série soit considérée comme du "burst" et surlignée.
RUN_THRESHOLD = 3

# Tolérance relative pour considérer deux phrases comme "de longueur égale"
# en nombre de syllabes. 0.30 = 30 % : une phrase de 20 syllabes est
# regroupée avec toutes les phrases suivantes du même bloc dont le nombre
# de syllabes reste à +/- 30 % de la phrase de référence (la 1ère de la
# série), soit ici entre 14 et 26 syllabes. En descendre trop (ex: 0.10)
# détecte peu de séries en pratique sur du texte réel.
LENGTH_TOLERANCE = 0.30

# --- Palette de couleur : chaque série jugée par SA PROPRE médiane -----
#
# Le document entier n'entre jamais en jeu. Chaque série de burst est
# traitée entièrement pour elle-même : on calcule la médiane des
# longueurs DE CETTE SÉRIE (sa propre référence interne), puis chaque
# phrase de la série reçoit une couleur de cette liste fixe selon
# l'écart entre SA longueur et CETTE médiane locale :
#   - la/les phrase(s) à la médiane de la série -> gris clair
#   - un peu plus longue que la médiane de la série -> jaune
#   - beaucoup plus longue -> rouge clair (plafond)
#   - un peu plus courte -> vert clair
#   - beaucoup plus courte -> bleu clair (plafond)
#
# La liste doit avoir un nombre IMPAIR d'entrées : celle du milieu est le
# gris de référence.
COLOR_SCALE = [
    "#cfe2ff",  # bleu clair - nettement plus courte que la médiane de SA série
    "#d9f2d9",  # vert clair - un peu plus courte que la médiane de SA série
    "#eeeeee",  # gris clair - à la médiane de SA série
    "#fff6cc",  # jaune clair - un peu plus longue que la médiane de SA série
    "#ffd9cc",  # rouge clair - nettement plus longue que la médiane de SA série
]

# Pas de seuil, pas de tolérance, pas de pondération par écart : le choix
# de couleur se fait uniquement par ORDRE (rang) des longueurs DISTINCTES
# présentes DANS LA SÉRIE, par rapport à sa propre médiane. Voir
# color_scale.colors_for_run().
