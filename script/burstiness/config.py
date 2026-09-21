"""
Réglages du détecteur de burstiness.

Modifie ces valeurs pour changer le comportement par défaut du script
(elles peuvent aussi être surchargées en ligne de commande, voir cli.py).
"""

# Méthode utilisée pour découper un texte en phrases :
#   "spacy" -> segmentation via spaCy (voir SPACY_FRENCH_MODEL), plus
#              robuste sur les cas piégeux (guillemets, dialogue...),
#              mais nécessite spaCy installé + le modèle téléchargé.
#   "regex" -> regex maison, zéro dépendance, un peu moins fine sur
#              certains cas particuliers.
SENTENCE_SPLIT_MODE = "regex"

# Modèle spaCy français utilisé quand SENTENCE_SPLIT_MODE = "spacy" (le
# même modèle que script/detector, déjà présent dans requirements.txt du
# dépôt — pip install spacy + ce modèle, aucune dépendance supplémentaire).
SPACY_FRENCH_MODEL = "fr_core_news_lg"

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

# Tolérance pour considérer deux phrases CONSÉCUTIVES comme "proches" en
# longueur (comme le ferait un lecteur : on compare chaque phrase à sa
# voisine immédiate, pas à une médiane de série ni à une statistique du
# document entier).
#
# Le seuil suit la loi de Weber-Fechner (psychophysique de la perception
# des quantités) : l'écart perceptible entre deux longueurs croît avec la
# RACINE CARRÉE de leur grandeur, pas proportionnellement à elle, et pas
# selon un nombre de mots fixe. Concrètement :
#
#     marge tolérée = LENGTH_TOLERANCE_K * sqrt(longueur moyenne des deux)
#
# Un lecteur remarque 1 mot d'écart entre deux phrases de 3-4 mots
# (marge ~1.7 avec K=1.0), mais pas 4 mots d'écart entre deux phrases de
# 26-30 mots (marge ~5.3) -- et ça se généralise tout seul à un texte à la
# Proust aux phrases de 60-80 mots (marge ~8-9), sans aucun plafond ni
# plancher fixé en mots. Voir burst_detect._is_close().
#
# LENGTH_TOLERANCE_K est un coefficient sans dimension : 1.0 = normal,
# <1.0 = plus strict (moins de séries détectées), >1.0 = plus permissif
# (au-delà de ~1.5-2.0, des séries incohérentes commencent à apparaître
# par dérive progressive, à éviter). C'est le seul réglage à ajuster si la
# détection te semble trop ou pas assez sensible.
LENGTH_TOLERANCE_K = 1.0

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
