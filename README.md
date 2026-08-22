# Unshiter — analyse statistique de textes

Unshiter compare des textes français à partir de mesures reproductibles : ponctuation, rythme, répétitions lexicales et sonores, structures syntaxiques, catégories grammaticales et statistiques de longueur. Les résultats décrivent un corpus ; ils ne constituent ni une preuve d’origine humaine ou artificielle, ni un jugement littéraire.

## Installation

```bash
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
```

Le calcul syntaxique utilise spaCy et le modèle français `fr_core_news_lg`. Morphalou et Démonette sont indexés dans `assets/`. Tous les chemins utilisés par les modules sont centralisés dans `script/detector/config.py`.

## Flux de travail

La base SQLite `assets/unshiter.sqlite3` est la source de vérité. Les scripts ne recalculent une œuvre que si son Markdown, la version d’analyse ou les données nécessaires ont changé.

### Ajouter ou actualiser des EPUB

Les EPUB sont déposés dans `_epub/`. L’extraction produit un Markdown normalisé dans le même dossier ; les préliminaires, titres, citations et paragraphes sont convertis selon le balisage de l’EPUB. La première fenêtre d’analyse est limitée à la taille configurée dans `config.py`.

```bash
./epubs.sh
```

Pour traiter une source précise (`.epub`, `.md` ou ancienne entrée `.avif`) :

```bash
./epubs.sh _epub/mon-livre.epub
```

La commande met à jour la base, supprime les livres disparus et signale les publications sans date. Les corrections éditoriales (titre ou année) se font dans `assets/publication.yml` ; les entrées sont conservées lors des actualisations.

Les Markdown placés dans `sources/` sont également indexés. Un nom qui ne commence pas par `_` est classé `IA` ; les autres sources sont humaines. Chaque fichier IA reste une œuvre distincte dans la base et dans le rapport.

### Générer le rapport README

```bash
./readme.sh
```

`readme.sh` ne fait que produire le rapport comparatif à partir de la base SQLite et actualiser le bloc statistique de ce README. Il génère :

- `_output/stats_comparison.md` : les tableaux comparatifs et leurs notes ;
- `_output/kiviat.svg`, `_output/kiviat_details.svg` et `_output/kiviat_areas.svg` : radars et surfaces ;
- `_output/grammatical_distribution.svg` : répartitions grammaticales.

Les mesures marquées `{windows}` dans `assets/stats-notes.md` sont calculées sur des fenêtres comparables ; les mesures techniques (mots, caractères, phrases, paragraphes) portent sur le document complet. Le cache est conservé dans `_temp/`.

### Générer le site web

```bash
./web.sh
```

Le site est une application statique dans `web/`. `web.sh` exporte la base SQLite en `web/data.json`, copie le prompt d’interprétation et ajoute une version aux ressources pour éviter les anciens fichiers en cache. Il n’accède pas aux Markdown : l’extraction et la synchronisation de la base relèvent de `epubs.sh`.

Le site permet de :

- sélectionner des auteurs et des œuvres ;
- choisir les mesures du radar et inverser leur sens ;
- afficher les limites du corpus, les moyennes par auteur ou les œuvres ;
- consulter la couverture stylistique, les évolutions par année et les tableaux complets ;
- télécharger les graphiques en PNG ou SVG ;
- sauvegarder des sélections dans le navigateur ;
- exporter le prompt d’analyse et les données JSON correspondant aux œuvres sélectionnées.

Pour le tester localement :

```bash
python3 -m http.server 8000 --directory web
```

Puis ouvrir <http://localhost:8000/>.

### Autres commandes

```bash
./publication-dates.sh          # recherche et met en cache les dates manquantes
PYTHONPATH=script python3 -m unittest discover -s script/detector/tests -v
```

<!-- STATS:START -->
## Dernier résultat

Ces tableaux et leurs notes sont actualisés automatiquement par `./readme.sh`.

### Synthèse

| Mesure | Roman duras | Roman FourthWing | Isa | L amant duras marguerite | Les particules elementaires michel houellebecq | Ravel jean echenoz | Vies minuscules michon pierre | σ[^1] |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Densité de ponctuations | 21.5 % | 18.5 % | 19.4 % | 16.7 % | 17.7 % | 14.6 % | 16.9 % | 11.4 % |
| Diversité de ponctuation | 58 % | 55 % | 63 % | 41 % | 67 % | 46 % | 60 % | 15.3 % |
| Diversité des structures | 51 % | 60 % | 50 % | 53 % | 53 % | 61 % | 66 % | 9.8 % |
| Rythme des structures | 51 % | 57 % | 50 % | 51 % | 47 % | 53 % | 59 % | 7.5 % |
| Profondeur syntaxique | 3.2 | 4.3 | 3.1 | 3.4 | 3.6 | 4.9 | 4.4 | 16.3 % |
| Diversité des débuts de phrase | 71 % | 67 % | 71 % | 60 % | 75 % | 77 % | 76 % | 8.0 % |
| Burstiness | 0.69 | 0.80 | 0.71 | 0.79 | 0.57 | 0.60 | 0.86 | 13.9 % |
| Ratio noms/verbes | 1.92 | 1.94 | 2.06 | 1.87 | 2.03 | 2.11 | 2.17 | 5.1 % |
| Répétitions lexicales | 14 % | 13 % | 9 % | 17 % | 10 % | 11 % | 9 % | 22.3 % |

### Détails

| Mesure | Roman duras | Roman FourthWing | Isa | L amant duras marguerite | Les particules elementaires michel houellebecq | Ravel jean echenoz | Vies minuscules michon pierre | σ[^1] |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Diversité stylistique | 82.0 % | 82.9 % | 90.3 % | 71.9 % | 89.6 % | 89.4 % | 89.5 % | 7.4 % |
| Répétitions familiales | 16 % | 15 % | 11 % | 19 % | 13 % | 13 % | 12 % | 17.3 % |
| Répétitions sonores | 21 % | 21 % | 21 % | 20 % | 22 % | 20 % | 20 % | 3.4 % |
| Répétitions non filtrées | 60 % | 60 % | 55 % | 66 % | 54 % | 54 % | 53 % | 7.6 % |
| Répétition globale des trigrammes | 3.4 % | 3.5 % | 1.1 % | 4.4 % | 1.5 % | 1.2 % | 0.9 % | 58.0 % |
| Répétition locale des trigrammes | 0.9 % | 1.2 % | 0.1 % | 2.0 % | 0.7 % | 0.2 % | 0.1 % | 87.2 % |
| Mots-outils | 39 % | 40 % | 39 % | 40 % | 35 % | 37 % | 36 % | 5.3 % |
| Noms | 33 % | 32 % | 34 % | 32 % | 35 % | 35 % | 34 % | 3.7 % |
| Verbes | 17 % | 16 % | 17 % | 17 % | 17 % | 17 % | 16 % | 2.8 % |
| Adjectifs | 4 % | 4 % | 4 % | 3 % | 5 % | 4 % | 6 % | 13.3 % |
| Adverbes | 6 % | 7 % | 5 % | 6 % | 6 % | 6 % | 5 % | 11.9 % |
| Diversité de longueurs de phrase (mots) | 6.2 | 24.1 | 9.3 | 14.0 | 12.5 | 14.8 | 41.1 | 41.1 % |
| Compression gzip | 34 % | 33 % | 38 % | 34 % | 37 % | 38 % | 38 % | 5.7 % |
| Relatives et subordonnées | 127 % | 265 % | 98 % | 132 % | 112 % | 270 % | 196 % | 39.1 % |
| Phrases nominales | 28 % | 27 % | 19 % | 11 % | 10 % | 11 % | 10 % | 45.1 % |
| Voix active | 66 % | 66 % | 67 % | 70 % | 73 % | 77 % | 77 % | 6.5 % |
| Comparaisons métaphoriques | 5.6 % | 12.8 % | 3.3 % | 6.3 % | 3.1 % | 9.7 % | 12.8 % | 50.1 % |
| Formes par lemme | 0.89 | 0.88 | 0.85 | 0.92 | 0.88 | 0.87 | 0.86 | 2.3 % |
| Mots employés une seule fois | 43 % | 41 % | 54 % | 52 % | 48 % | 59 % | 55 % | 12.1 % |
| Mots | 40970 | 56777 | 49521 | 29525 | 89770 | 22553 | 58719 | — |
| Phrases | 3118 | 2224 | 3585 | 1982 | 4774 | 878 | 1343 | — |
| Paragraphes | 939 | 940 | 774 | 257 | 665 | 146 | 274 | — |
| Longueur moyenne des mots (caractères) | 4.5 | 4.6 | 4.8 | 4.4 | 5.0 | 4.7 | 4.8 | — |
| Longueur moyenne des phrases (caractères) | 75.4 | 147.8 | 81.2 | 81.7 | 116.1 | 149.0 | 262.6 | — |
| Longueur moyenne des phrases (mots) | 13.9 | 27.1 | 14.8 | 15.9 | 20.0 | 27.5 | 46.8 | — |
| Longueur médiane des phrases (caractères) | 62.0 | 112.0 | 64.0 | 59.0 | 98.0 | 138.0 | 211.0 | — |
| Longueur P10 des phrases (caractères) | 21.0 | 21.0 | 24.0 | 22.0 | 38.0 | 38.0 | 39.0 | — |
| Longueur P90 des phrases (caractères) | 147.0 | 331.0 | 159.0 | 162.0 | 214.0 | 267.0 | 546.0 | — |
| Écart-type des paragraphes (mots) | 30.6 | 42.9 | 45.7 | 118.0 | 125.4 | 62.6 | 156.1 | — |
| Fenêtres analysées | 2 | 2 | 2 | 1 | 4 | 1 | 2 | — |
| Longueur moyenne des paragraphes (mots) | 43.6 | 60.4 | 64.0 | 114.9 | 135.0 | 154.5 | 214.3 | — |

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
<!-- STATS:END -->

Une empreinte SHA-256 identifie le contenu du corpus dans `_temp/stats-cache.json`. Les mesures sont enregistrées séparément pour chaque document et les calculs susceptibles d’évoluer possèdent leur propre version. Modifier `assets/stats-notes.md` ne recalcule aucune mesure : `./readme.sh` régénère seulement le rapport et le README.

## Méthode de comparaison

Les textes n’ont pas tous la même taille. Pour éviter qu’un roman bénéficie simplement d’un plus grand échantillon, les mesures dérivées sont calculées sur des fenêtres non chevauchantes ayant pour cible le nombre de mots du texte le plus court.

Une fenêtre se termine toujours à la fin d’un paragraphe. Elle peut donc dépasser légèrement la cible. Si la dernière fenêtre contient moins de 70 % de la cible, elle n’est pas prise en compte. Lorsqu’un texte entier est plus court que ce seuil et ne fournit aucune autre fenêtre, il reste analysé comme un seul bloc. Les mesures des fenêtres retenues sont ensuite moyennées pour chaque document.

Gzip suit une règle différente : ses blocs sont découpés en octets UTF-8 et ont exactement la taille du texte le plus court en octets. Les comptages techniques — mots, phrases et paragraphes — décrivent toujours le document complet.


## Graphiques du rapport

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
- `_epub/` : EPUB et Markdown extraits ;
- `sources/` : corpus Markdown indépendant ;
- `web/` : application statique et données exportées ;
- `assets/unshiter.sqlite3` : base statistique ;
- `_output/` : rapports générés ;
- `_temp/` : cache et fichiers temporaires.

Tous les chemins sont définis dans `script/detector/config.py`.

`assets/stats-notes.md` est le texte éditorial des notes affichées dans le rapport. Après la présente réécriture, il ne doit plus être modifié automatiquement : toute proposition ultérieure doit être formulée en commentaire afin de laisser le dernier mot à son auteur.

## Tests

```bash
PYTHONPATH=script python3 -m unittest discover -s script/detector/tests -v
```
