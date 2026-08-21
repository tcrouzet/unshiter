# Unshiter — analyse statistique de textes

Unshiter compare des textes français sans demander à un modèle génératif de les juger. Il mesure leur ponctuation, leur rythme, leurs répétitions, leurs structures syntaxiques et leur répartition grammaticale. Les résultats décrivent les textes du corpus ; ils ne constituent pas une preuve d’origine humaine ou artificielle.

## Installation

```bash
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
```

Le projet utilise spaCy 3.8.13 avec le modèle français `fr_core_news_lg` 3.8.0. Le modèle est installé par `requirements.txt`.

## Lancer une comparaison

Placez les fichiers Markdown dans `sources/`, puis lancez :

```bash
./stats.sh
```

Les fichiers sont classés ainsi :

- un fichier sans `_` initial est considéré comme un texte IA ;
- tous les fichiers IA sont fusionnés dans une seule colonne `IA` ;
- un fichier commençant par `_` est considéré comme humain ;
- les textes humains sont affichés après `IA`, par ordre alphabétique ;
- le `_` initial et l’extension `.md` ne sont pas affichés dans les titres.

Pour analyser un seul fichier et produire ses rapports Markdown et JSON :

```bash
./stats.sh sources/IA.md
```

## Fichiers produits

Les sorties sont écrites dans `_output/` :

- `stats_comparison.md` : tableaux comparatifs et graphiques intégrés ;
- `kiviat.svg` : radar des mesures du tableau principal ;
- `kiviat_details.svg` : radar des mesures du tableau détaillé dont σ atteint au moins 10 % ;
- `kiviat_areas.svg` : surface des profils du radar, classée par ordre croissant ;
- `grammatical_distribution.svg` : camemberts grammaticaux, trois par ligne ;
- `*_structure.md` : phrases et structures reconnues ;
- `*_lemmes.md` : textes lemmatisés avec répétitions signalées.

<!-- STATS:START -->
## Dernier résultat

Ces tableaux et leurs notes sont actualisés automatiquement par `./stats.sh`.

### Synthèse

| Mesure | IA | Crouzet | Duras | Echenoz | Houellebecq | Michon | σ[^1] |
|---|---:|---:|---:|---:|---:|---:|---:|
| Ponctuation (signes/300 mots) | 36.1 | 57.9 | 50.2 | 43.4 | 52.7 | 50.6 | 14.4 % |
| Diversité de ponctuation | 40 % | 61 % | 40 % | 45 % | 64 % | 58 % | 19.5 % |
| Diversité des structures | 42 % | 48 % | 53 % | 61 % | 53 % | 65 % | 14.3 % |
| Rythme des structures | 41 % | 49 % | 51 % | 53 % | 47 % | 59 % | 11.0 % |
| Profondeur syntaxique | 3.7 | 3.2 | 3.5 | 5.1 | 3.7 | 4.5 | 16.1 % |
| Diversité des débuts de phrase | 52 % | 72 % | 59 % | 78 % | 76 % | 76 % | 14.1 % |
| Burstiness | 0.69 | 0.67 | 0.79 | 0.60 | 0.58 | 0.87 | 14.6 % |
| Ratio noms/verbes | 1.56 | 2.09 | 1.88 | 2.17 | 2.06 | 2.20 | 5.4 % |
| Répétitions lexicales | 9 % | 10 % | 16 % | 12 % | 12 % | 9 % | 11.5 % |

### Détails

| Mesure | IA | Crouzet | Duras | Echenoz | Houellebecq | Michon | σ[^1] |
|---|---:|---:|---:|---:|---:|---:|---:|
| Diversité stylistique | 90.4 % | 86.5 % | 72.1 % | 86.2 % | 86.0 % | 89.8 % | 2.2 % |
| Répétitions familiales | 12 % | 12 % | 18 % | 14 % | 14 % | 12 % | 9.6 % |
| Répétitions sonores | 20 % | 19 % | 20 % | 20 % | 22 % | 19 % | 2.4 % |
| Répétitions non filtrées | 55 % | 53 % | 64 % | 53 % | 53 % | 51 % | 2.4 % |
| Répétition globale des trigrammes | 1.6 % | 1.3 % | 3.5 % | 1.0 % | 1.7 % | 0.7 % | 30.3 % |
| Répétition locale des trigrammes | 0.3 % | 0.5 % | 1.9 % | 0.3 % | 0.8 % | 0.2 % | 51.3 % |
| Mots-outils | 43 % | 39 % | 40 % | 37 % | 35 % | 36 % | 6.8 % |
| Noms | 29 % | 35 % | 32 % | 35 % | 35 % | 35 % | 3.1 % |
| Verbes | 19 % | 17 % | 17 % | 17 % | 17 % | 16 % | 3.3 % |
| Adjectifs | 4 % | 5 % | 3 % | 4 % | 5 % | 6 % | 20.4 % |
| Adverbes | 6 % | 5 % | 6 % | 6 % | 6 % | 5 % | 11.6 % |
| Diversité de longueurs de phrase (mots) | 7.8 | 8.7 | 13.7 | 15.4 | 12.0 | 37.4 | 25.1 % |
| Compression gzip | 42 % | 46 % | 41 % | 45 % | 45 % | 46 % | 4.2 % |
| Relatives et subordonnées | 131 % | 104 % | 135 % | 279 % | 118 % | 207 % | 37.7 % |
| Phrases nominales | 7 % | 21 % | 10 % | 10 % | 10 % | 10 % | 3.6 % |
| Voix active | 81 % | 66 % | 70 % | 77 % | 73 % | 77 % | 6.9 % |
| Comparaisons métaphoriques | 2.1 % | 3.4 % | 6.3 % | 9.9 % | 3.2 % | 12.8 % | 61.8 % |
| Formes par lemme | 0.83 | 0.85 | 0.91 | 0.87 | 0.88 | 0.86 | 1.9 % |
| Mots employés une seule fois | 72 % | 76 % | 66 % | 75 % | 74 % | 77 % | 2.3 % |
| Mots | 1743 | 49880 | 29454 | 22614 | 91510 | 58784 | — |
| Phrases | 134 | 4088 | 1972 | 877 | 4811 | 1336 | — |
| Paragraphes | 33 | 834 | 248 | 153 | 889 | 282 | — |
| Longueur moyenne des mots (caractères) | 5.0 | 4.8 | 4.4 | 4.7 | 5.0 | 4.8 | — |
| Longueur moyenne des phrases (caractères) | 78.6 | 73.3 | 83.9 | 154.7 | 123.0 | 276.7 | — |
| Longueur moyenne des phrases (mots) | 13.0 | 12.4 | 15.3 | 26.7 | 19.8 | 46.1 | — |
| Longueur médiane des phrases (caractères) | 67.5 | 59.8 | 62.6 | 144.4 | 106.5 | 222.5 | — |
| Longueur P10 des phrases (caractères) | 29.3 | 23.0 | 23.4 | 49.9 | 45.2 | 51.4 | — |
| Longueur P90 des phrases (caractères) | 145.6 | 139.9 | 164.2 | 264.3 | 218.9 | 567.8 | — |
| Écart-type des paragraphes (mots) | 34.4 | 40.2 | 105.8 | 62.0 | 107.7 | 129.5 | — |
| Fenêtres analysées | 1 | 28 | 16 | 12 | 49 | 31 | — |
| Longueur moyenne des paragraphes (mots) | 52.8 | 66.5 | 127.0 | 150.8 | 126.5 | 234.9 | — |

### Profil comparatif

![Profils comparatifs](./assets/readme/kiviat-github.png)

Le diagramme reprend exactement les mesures du tableau principal. L’anneau médian représente la moyenne du corpus avec le même gris que les autres lignes de lecture. Les écarts relatifs à cette moyenne sont amplifiés pour rendre les profils lisibles ; les répétitions lexicales sont inversées afin que l’extérieur indique toujours davantage de diversité ou de complexité.


### Profil des mesures secondaires

![Radar des mesures secondaires](./assets/readme/kiviat-details-github.png)

Ce radar reprend les mesures du tableau 2 dont la dispersion σ atteint au moins 10 %, en excluant la diversité de longueur des phrases déjà intégrée à la diversité des structures. Les répétitions, les adjectifs, les adverbes, les relatives et subordonnées et les comparaisons métaphoriques sont inversés : pour ces indices négatifs, l’extérieur correspond à une valeur plus faible. Pour les autres axes, l’extérieur correspond à une valeur plus élevée.


### Surface des profils

![Surface des profils](./assets/readme/kiviat-areas-github.png)

Les surfaces sont calculées directement sur les polygones du radar et classées de la plus petite à la plus grande. Leur unité est arbitraire.


### Répartition grammaticale par document

![Répartition grammaticale](./assets/readme/grammatical-distribution-github.png)


[^1]: Indique à quel point les valeurs diffèrent dans le corpus. Le calcul commence par écarter les valeurs aberrantes selon la règle de Tukey : toute valeur située à plus de 1,5 fois l’intervalle interquartile sous le premier quartile ou au-dessus du troisième quartile est ignorée. Elle reste affichée dans le tableau, mais ne gonfle pas σ. L’écart-type des valeurs restantes est ensuite divisé par leur moyenne et affiché en pourcentage. Un σ faible signale une mesure non significative.
<!-- STATS:END -->

Une empreinte SHA-256 identifie le contenu du corpus dans `_temp/stats-cache.json`. Les mesures sont enregistrées séparément pour chaque document et les calculs susceptibles d’évoluer possèdent leur propre version. Modifier le calcul des trigrammes ne recalcule donc que les deux mesures de trigrammes ; les résultats spaCy, phonétiques, grammaticaux et les autres valeurs restent en cache. Modifier `assets/stats-notes.md` ne recalcule aucune mesure : `./stats.sh` régénère seulement le rapport et le README.

## Fenêtres de comparaison

Les textes n’ont pas tous la même taille. Pour éviter qu’un roman bénéficie simplement d’un plus grand échantillon, les mesures dérivées sont calculées sur des fenêtres non chevauchantes ayant pour cible le nombre de mots du texte le plus court.

Une fenêtre se termine toujours à la fin d’un paragraphe. Elle peut donc dépasser légèrement la cible. Si la dernière fenêtre contient moins de 70 % de la cible, elle n’est pas prise en compte. Lorsqu’un texte entier est plus court que ce seuil et ne fournit aucune autre fenêtre, il reste analysé comme un seul bloc. Les mesures des fenêtres retenues sont ensuite moyennées pour chaque document.

Gzip suit une règle différente : ses blocs sont découpés en octets UTF-8 et ont exactement la taille du texte le plus court en octets. Les comptages techniques — mots, phrases et paragraphes — décrivent toujours le document complet.


## Graphiques

Le radar reprend exactement les mesures du tableau principal. Pour chaque axe, le rayon médian correspond à la moyenne du corpus. La position vaut `0,5 + 1,25 × (valeur − moyenne) / moyenne`, limitée entre 0,05 et 1. Les répétitions lexicales sont inversées afin que l’extérieur corresponde à moins de répétitions. Toutes les lignes de lecture utilisent le même gris.

L’histogramme des surfaces applique la formule géométrique de l’aire à chaque polygone du radar, puis classe les auteurs de la plus petite à la plus grande surface. Son unité est arbitraire et dépend des axes retenus, de leur ordre et de l’amplification du radar.

## Limites

- Les résultats dépendent du découpage en phrases, des dictionnaires et du modèle spaCy.
- Morphalou analyse les formes hors contexte et peut conserver des ambiguïtés.
- Les ellipses, incises, phrases nominales et constructions littéraires peuvent dégrader l’analyse spaCy.
- Une mesure très dispersée dans le corpus actuel ne le sera pas nécessairement dans un autre corpus.
- Les graphiques résument les mesures choisies ; ils ne calculent pas une probabilité d’origine IA.

## Organisation du projet

- `script/detector/` : calculs, interface et tests ;
- `assets/` : Morphalou, Démonette, mots-outils et notes du rapport ;
- `sources/` : corpus Markdown ;
- `_output/` : rapports générés ;
- `_temp/` : cache et fichiers temporaires.

Tous les chemins sont définis dans `script/detector/config.py`.

`assets/stats-notes.md` est le texte éditorial des notes affichées dans le rapport. Après la présente réécriture, il ne doit plus être modifié automatiquement : toute proposition ultérieure doit être formulée en commentaire afin de laisser le dernier mot à son auteur.

## Tests

```bash
PYTHONPATH=script python3 -m unittest discover -s script/detector/tests -v
```
