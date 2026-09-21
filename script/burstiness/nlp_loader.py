"""
Chargement partagé du modèle spaCy français, utilisé pour la
segmentation de phrases (voir sentence_split.py).

C'est le même modèle que celui déjà utilisé par script/detector dans ce
dépôt (voir requirements.txt à la racine) : aucune dépendance
supplémentaire à installer si le reste du projet fonctionne déjà.

Le modèle est volumineux à charger (fr_core_news_lg) : on le met en
cache pour ne le charger qu'une seule fois par exécution, quel que soit
le nombre de blocs/paragraphes traités. On exclut aussi les composants
inutiles pour du simple découpage en phrases (NER, lemmatiseur) : ça
accélère à la fois le chargement du modèle et l'analyse de chaque
document, sans toucher à la segmentation elle-même (assurée par le
parser, jamais désactivé).
"""

from functools import lru_cache

import spacy

from . import config

# Composants du pipeline spaCy dont on n'a pas besoin pour segmenter des
# phrases : les exclure évite de charger leurs poids ET de les exécuter.
_EXCLUDED_COMPONENTS = ["ner", "lemmatizer"]


@lru_cache(maxsize=1)
def get_nlp():
    return spacy.load(config.SPACY_FRENCH_MODEL, exclude=_EXCLUDED_COMPONENTS)
