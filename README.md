# Unshiter — détecteur statistique

Analyse comparative de textes français : rythme, répétitions, structures
syntaxiques, répartition grammaticale et indice IA expérimental.

## Utilisation

Placez les fichiers Markdown à comparer dans `sources/`, puis lancez :

```bash
./stats.sh
```

Le rapport comparatif, les structures et le graphique grammatical sont générés
dans `_output/`.

Pour analyser un fichier précis et produire ses rapports Markdown et JSON :

```bash
./stats.sh sources/lettre1.md
```

## Installation

```bash
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
```

## Organisation

- `script/detector/` : code du détecteur statistique ;
- `assets/` : base Morphalou, mots-outils et notes des mesures ;
- `sources/` : corpus Markdown versionnable ;
- `_output/` : rapports générés, non versionnés ;
- `script/detector/tests/` : tests automatisés du détecteur.

Tous les chemins utilisés par le détecteur sont centralisés dans
`script/detector/config.py`.

## Mesures

Les mesures comparatives sont calculées sur des fenêtres ayant la taille du
texte le plus court. Les textes longs sont découpés en fenêtres décalées, puis
leurs résultats sont moyennés. Les nombres de mots, phrases et paragraphes
décrivent toutefois le document complet.

### Synthèse et indice IA

| Mesure | Calcul et interprétation |
|---|---|
| Δ | Écart entre le texte IA de référence et la moyenne des textes humains de référence, rapporté au maximum théorique ou observé. Une valeur proche de 0 % indique que la mesure distingue peu les deux groupes sur le corpus actuel. |
| IA | Somme de sept signaux normalisés. Ce résultat est un indice expérimental, pas une probabilité. Les bornes et les poids sont définis dans `config.py`. |
| Répétition des structures | Part des phrases dont le patron syntaxique apparaît plusieurs fois. Les patrons sont produits par Morphalou et des règles locales, pas par l’analyse de dépendances spaCy. Les structures réduites au seul rôle `INCONNU` sont écartées. Une valeur élevée augmente l’indice IA. |
| Diversité des structures | Nombre de patrons distincts divisé par le nombre total de phrases analysées. Une valeur faible signifie que quelques constructions dominent et augmente l’indice IA. |
| Relatives et subordonnées | Nombre de dépendances `acl:relcl`, `acl`, `advcl`, `ccomp`, `csubj` et `xcomp`, divisé par le nombre de phrases. Une phrase pouvant contenir plusieurs propositions, la valeur peut dépasser 100 %. Une valeur élevée augmente légèrement l’indice IA. |
| Ponctuation | Nombre de signes parmi `.,;:!?…—–-()«»"` pour 300 mots. Une faible densité augmente l’indice IA. |
| Diversité de ponctuation | Part des catégories de ponctuation effectivement employées parmi celles reconnues. Une faible diversité augmente l’indice IA. |
| Phrases nominales | Part des phrases sans verbe ou auxiliaire fini selon spaCy. Une faible valeur augmente légèrement l’indice IA. |
| Variété des débuts de phrase | Diversité des premiers mots des phrases, moyennée localement. Une faible variété augmente l’indice IA. |

Poids actuels de l’indice IA : répétition des structures 25 %, faible diversité
des structures 20 %, faible densité de ponctuation 15 %, faible diversité de
ponctuation 15 %, faible variété des débuts 15 %, faible taux de phrases
nominales 5 %, relatives et subordonnées 5 %.

### Rythme et longueur des phrases

| Mesure | Calcul et interprétation |
|---|---|
| Amplitude (caractères) | Différence entre le 90e et le 10e percentile des longueurs de phrases. Elle décrit l’étendue habituelle sans donner trop de poids aux phrases extrêmes. |
| Variation des phrases (mots) | Écart-type du nombre de mots par phrase. Une valeur élevée indique des longueurs plus dispersées. |
| Burstiness | Moyenne des écarts absolus, en caractères, entre deux phrases consécutives, divisée par la longueur moyenne des phrases. La division rend comparables des textes composés de phrases courtes ou longues. |
| Rythme des structures | Distance d’édition moyenne entre deux patrons syntaxiques consécutifs, divisée par la longueur du patron le plus long. 0 % indique une succession de patrons identiques. |

### Répétitions et vocabulaire

Toutes les répétitions locales cherchent un antécédent parmi les 300 mots
précédents. Les apostrophes sont séparées et les graphies de moins de deux
caractères sont ignorées dans les annotations.

| Mesure | Calcul et interprétation |
|---|---|
| Répétitions stylistiques | Pression pondérée des répétitions locales : graphie identique à poids plein, même lemme ou même famille à poids 0,25. Les mots-outils et noms propres sont exclus. Une répétition concentrée pèse davantage que des occurrences isolées. |
| Répétitions lexicales | Part des mots reprenant un lemme déjà rencontré dans l’empan local. Morphalou regroupe les flexions ; les mots-outils sont exclus. |
| Répétitions familiales | Même principe, mais Démonette regroupe aussi les mots d’une famille morphologique, par exemple *écrire*, *écrivain* et *écriture*. |
| Répétitions sonores | Part des mots partageant une séquence phonétique significative avec un mot récent. Le seuil minimal est une séquence de trois phonèmes couvrant au moins 60 % de la prononciation. |
| Taux de répétition non filtré | Répétition des lemmes calculée en conservant les mots-outils. Cette valeur mesure aussi les répétitions grammaticales ordinaires. |
| Diversité des formes | Nombre de graphies distinctes divisé par le nombre de mots de chaque fenêtre, puis moyenne des fenêtres. Les flexions différentes restent distinctes. |
| Diversité lemmatisée | Nombre de lemmes distincts divisé par le nombre de mots de chaque fenêtre. Les flexions reconnues par Morphalou sont regroupées. |
| Mots employés une seule fois | Part des formes graphiques dont la fréquence vaut exactement un dans la fenêtre. |
| Répétition globale des trigrammes | Part des suites de trois mots apparaissant plusieurs fois dans tout le texte analysé. |
| Répétition locale des trigrammes | Même mesure, calculée dans des fenêtres locales puis moyennée. Elle repère les répétitions de formulations proches. |
| Compression gzip | Taille gzip du texte UTF-8 divisée par sa taille originale. Une faible valeur indique un texte plus compressible, donc plus redondant ou prévisible. |

### Grammaire et syntaxe

L’analyse contextuelle utilise spaCy `fr_core_news_lg` 3.8.0. Les patrons de
structures, eux, utilisent Morphalou et des règles explicites ; ils ne reposent
pas sur l’arbre de dépendances spaCy.

| Mesure | Calcul et interprétation |
|---|---|
| Mots-outils | Part des déterminants, pronoms, prépositions, conjonctions et interjections. Les adverbes ne sont pas classés comme mots-outils. |
| Noms, verbes, adjectifs, adverbes | Répartition de ces quatre catégories parmi les mots appartenant à l’une d’elles. Le graphique sépare en plus noms communs et noms propres. |
| Profondeur syntaxique | Pour chaque phrase, distance maximale entre un mot et la racine de l’arbre de dépendances, puis moyenne des phrases. Cette mesure dépend directement du modèle spaCy et n’entre pas dans l’indice IA. |

### Données techniques du document

| Valeur | Définition |
|---|---|
| Mots, phrases, paragraphes | Comptages sur le document complet. Un ou plusieurs sauts de ligne vides séparent deux paragraphes. |
| Longueur moyenne des mots | Nombre moyen de caractères par mot. |
| Longueur moyenne des phrases | Moyenne en caractères, espaces compris, et moyenne en mots. |
| Médiane, P10 et P90 | Percentiles des longueurs de phrases en caractères. La médiane partage les phrases en deux groupes ; P10 et P90 délimitent les 10 % les plus courtes et les 10 % les plus longues. |
| Écart-type des phrases | Dispersion des longueurs de phrases en caractères autour de leur moyenne. |
| Écart-type des paragraphes | Dispersion du nombre de mots par paragraphe. |
| Fenêtres de répétition analysées | Nombre de fenêtres utilisées pour produire les moyennes comparables. |
| Longueur moyenne des paragraphes | Nombre moyen de mots par paragraphe. |

### Limites

L’indice IA est calibré manuellement sur le petit corpus présent dans
`sources/`. Un prompt stylistique, une réécriture humaine ou un changement de
genre peut modifier fortement les signaux. Les mesures issues de spaCy sont
également sensibles au modèle employé, particulièrement sur les ellipses,
incises et phrases nominales. Le rapport doit donc servir à comparer des textes,
pas à certifier leur origine.

## Tests

```bash
PYTHONPATH=script python3 -m unittest discover -s script/detector/tests -v
```
