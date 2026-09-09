# Unshiter — analyse statistique de textes

Unshiter compare des textes français à partir de mesures déterministes et reproductibles. Les résultats décrivent un corpus ; ils ne constituent ni une preuve d’origine humaine ou artificielle, ni un jugement littéraire.

[Plusieurs articles commentent cette exérience…](https://tcrouzet.com/tag/textstat/)

## Installation

```bash
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
```

Le calcul syntaxique utilise spaCy et le modèle français `fr_core_news_lg`. Morphalou et Démonette sont indexés dans `assets/`. Tous les chemins utilisés par les modules sont centralisés dans `script/detector/config.py`.

## Flux de travail

La base SQLite `assets/unshiter.sqlite3` est la source de vérité. Les scripts ne recalculent une œuvre que si son Markdown, la version d’analyse ou les données nécessaires ont changé.

### Ajouter ou actualiser des EPUB

Les EPUB peuvent être déposés n’importe où sous `corpus/<id>/`, avec autant de sous-dossiers que souhaité. L’extraction produit un Markdown normalisé à côté de chaque EPUB ; les préliminaires, titres, citations et paragraphes sont convertis selon son balisage. L’application web affiche `bigcorpus` par défaut.

```bash
./epubs.sh
./epubs.sh crouzet
./epubs.sh --reset
```

Sans argument, la commande parcourt tous les dossiers directs de `corpus/`. Avec un identifiant, elle ne traite que ce corpus. Dans les deux cas, elle conserve les mesures présentes et ne calcule que les fichiers modifiés ou les mesures manquantes. Elle supprime aussi les appartenances disparues et signale les publications sans date. Les corrections éditoriales (titre ou année) se font dans `assets/publication.yml` ; les entrées sont conservées lors des actualisations.

Avec `--reset`, la commande vide entièrement les tables SQLite d’analyse et de cache, recalcule tous les corpus, Big Five compris, puis régénère `web/data.json`. Les EPUB, les Markdown et `assets/publication.yml` sont conservés.

Tous les Markdown trouvés récursivement sous `corpus/<id>/` sont indexés. C’est le champ `author` de leur en-tête YAML qui détermine le classement : `author: "IA"` les place dans le groupe IA, quel que soit le nom du fichier ; toute autre valeur les classe parmi les textes humains. Une œuvre présente dans plusieurs corpus conserve une seule analyse, reconnue par son empreinte SHA-256.

### Actualiser le site et la documentation des métriques

```bash
./readme.sh
```

`readme.sh` actualise les données du site et remplace la section « Métriques » de ce README à partir de `assets/stats-notes.md`. Il ne produit plus de rapport comparatif, de tableau ou de graphique dans le README et ne relance aucune analyse spaCy.

### Générer le site web

```bash
./web.sh
```

<https://tcrouzet.github.io/unshiter/>

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

## Organisation du projet

- `script/detector/` : calculs, interface et tests ;
- `script/detector/config.py` : chemins et variables globales ;
- `assets/` : Morphalou, Démonette, mots-outils et notes du rapport ;
- `assets/stats-notes.md` : source des notes affichées sur le site et de la liste des métriques de ce README ;
- `assets/unshiter.sqlite3` : base statistique ;
- `corpus/<id>/` : arborescence libre contenant les EPUB et Markdown du corpus ;
- `web/` : application statique et données exportées ;
- `_temp/` : cache et fichiers temporaires.


## Ressources linguistiques

<a id="note_spacy"></a>
### spaCy (note_spacy)
Le modèle français `fr_core_news_lg` de [spaCy](https://spacy.io/models/fr) segmente le texte et fournit en contexte les lemmes, catégories grammaticales, traits morphologiques et dépendances syntaxiques. Il alimente notamment les comptes de propositions, verbes, participes, sujets, voix et modificateurs. Cette analyse est probabiliste : les phrases longues, elliptiques ou littéraires peuvent être mal segmentées ou mal étiquetées.

<a id="note_morphalou"></a>
##### Morphalou (note_morphalou)
[Morphalou 3.1](https://repository.ortolang.fr/api/content/morphalou/2/LISEZ_MOI.html) est un lexique morphologique du français utilisé pour relier les formes fléchies à leurs lemmes et catégories grammaticales. Il sert de repli ou de contrôle lorsque l’analyse contextuelle ne suffit pas. Comme il décrit des formes hors contexte, une graphie ambiguë peut correspondre à plusieurs analyses possibles.

<a id="note_lexique383"></a>
##### Lexique 3.83 (note_lexique383)
[Lexique 3.83](http://www.lexique.org/) fournit les fréquences d’usage qui alimentent la mesure de rareté lexicale. Une fréquence issue de ce corpus lexical ne représente pas nécessairement l’usage propre à une époque, un genre ou un auteur.

<a id="note_demonette"></a>
##### Démonette (note_demonette)
[Démonette](https://demonette.fr/) décrit les familles dérivationnelles du français, par exemple les relations entre « écrire », « écrivain » et « écriture ». Le projet l’utilise pour étendre les entrées du dictionnaire émotionnel à leurs lexèmes apparentés. Ses données phonétiques servent également au repérage des répétitions sonores. Ces rapprochements sont lexicaux et non contextuels : appartenir à une même famille ne garantit ni un sens identique dans la phrase ni une même valeur émotionnelle.

<a id="note_custom_lexicons"></a>
##### Dictionnaires maison (note_custom_lexicons)
Les fichiers texte de `assets/dictionnaires/` complètent les ressources générales par des listes adaptées aux mesures du projet : émotions, mots-outils, connecteurs temporels et logiques, verbes statifs ou modaux, pronoms génériques, marqueurs de durée, de comparaison, de familiarité et de négation, suffixes abstraits et exceptions concrètes. Chaque mesure indique le fichier précis qu’elle emploie. Ces listes sont explicites et modifiables, mais leur couverture reste artisanale : une absence n’implique pas l’absence linguistique du phénomène, et une présence ne résout ni la polysémie ni le contexte.

<!-- STATS:START -->
## Métriques

Les mesures sur les textes du corpus sont déterministes, reproductibles et visibles sur [l’application web](https://tcrouzet.github.io/unshiter/).

**Limites**

- Les résultats dépendent du découpage en phrases, des dictionnaires et du modèle [spaCy](https://github.com/explosion/spacy).
- [Morphalou](https://repository.ortolang.fr/api/content/morphalou/2/LISEZ_MOI.html) analyse les formes hors contexte et peut conserver des ambiguïtés.
- Les ellipses, incises, phrases nominales et constructions littéraires peuvent dégrader l’analyse spaCy.
- Une mesure très dispersée dans le corpus actuel ne le sera pas nécessairement dans un autre corpus.
- Les graphiques du site résument les mesures choisies ; ils ne calculent pas une probabilité d’origine IA.

### BigFive

Les BigFive synthétisent des familles de mesures complémentaires. Ils servent à comparer des profils stylistiques ; ils ne constituent ni un jugement de qualité ni une preuve d’origine humaine ou artificielle. Cette classification s'inspire de l'étude [LiteraryBigFive](https://github.com/Znull-1220/LiteraryBigFive). Les score sont normalisés, avec 100 % attribué au plus élevé du corpus.

<a id="classicism_score"></a>
##### **Classique** / Contemporain (classicism_score)
Score qui agrège l’usage des [subjonctifs imparfaits ou plus-que-parfaits](#literary_subjunctive_ratio), l’absence de [futur périphrastique](#periphrastic_future_ratio), l’absence de [familiarité orale](#oral_familiarity_ratio) en dehors des [dialogues](#dialogue_ratio), la [diversité syntaxique](#structural_diversity), un [style verbal](#noun_verb_ratio), une [voix active](#active_voice_ratio) et l'emploi des [points-virgules et deux-points](#punctuation_variety_score). Le [passé simple](#simple_past_ratio) reste une mesure indépendante et n’entre pas dans ce score.

**Limite :** le score mesure un registre narratif littéraire formel (grammaire et registre écrits, absence d'oralité), pas une esthétique historique précise. Un texte contemporain narré au [passé simple](#simple_past_ratio) ou au subjonctif littéraire peut afficher un registre écrit soigné sans rien partager avec l'esthétique du XVII<sup>e</sup> siècle.

<a id="baroque_score"></a>
##### **Maximaliste** / Minimaliste (baroque_score)
Score composite : proche de 0, minimalisme ; proche de 100, maximalisme. Il combine l'[enrichissement des groupes nominaux](#heavily_modified_noun_ratio), les [comparaisons](#metaphorical_comme_ratio), les [chaînes adjectivales](#adjective_chain_ratio), la [distance de répétition des débuts de phrase](#sentence_start_recurrence_distance), la [profondeur d'expansion en fin de phrase](#right_branching_depth), la [densité d'incises](#incise_density) et l'[accumulation de coordinations](#coordination_accumulation_ratio). La longueur moyenne des phrases reste une mesure indépendante afin de ne pas renforcer une seconde fois la complexité syntaxique.

**Limite :** plusieurs composantes sont sensibles à la qualité de l'analyse syntaxique et à la segmentation des phrases. Une prose générée artificiellement peut empiler des expansions ou espacer mécaniquement ses patrons sans réelle cohérence rhétorique — un pastiche peut ainsi obtenir un score élevé sans être « maximaliste » au sens littéraire du terme.

<a id="narrativity_score"></a>
##### **Narratif** / Descriptif (narrativity_score)
Proche de 100 %, récit d'action ; proche de 0, peinture descriptive. Le score combine les [verbes d'action](#action_verb_ratio), les [connecteurs temporels](#temporal_connector_ratio), les [dialogues](#dialogue_ratio), la [voix active](#active_voice_ratio), le [taux de rupture temporelle](#tense_shift_rate) entre paragraphes et la [densité de noms propres](#proper_noun_density), en retirant les [phrases nominales](#nominal_sentence_ratio) et la [densité d'adjectifs](#adjective_ratio). Le [passé narratif](#narrative_past_ratio) et le [taux de marqueurs de sommaire](#scene_summary_ratio) restent des mesures informatives séparées et n'entrent pas dans ce score.

**Limite :** un texte à phrases très courtes et fragmentées (écriture pour réseaux sociaux, par exemple) peut afficher un [taux de dialogue](#dialogue_ratio) et une accumulation d'adjectifs artificiellement bas faute de matière suffisante, ce qui peut gonfler le score sans que le texte soit réellement orienté vers l'action narrative.

<a id="emotionality_score"></a>
##### **Émotionnel** / Neutre (emotionality_score)
Score composite à trois composantes : la [part de phrases à caractère émotionnel](#emotion_sentence_ratio), l'[intensification émotionnelle](#emotion_intensification_ratio) et L'[entropie des registres émotionnels](#emotional_category_entropy). Il décrit une densité et une gradation d'expression affective explicite détectée par lexique, pas la qualité ni la valence positive ou négative du texte, ni une charge émotionnelle exprimée par litote ou par déplacement narratif.

**Limite :** ce score ne peut détecter que la présence et l'intensité de vocabulaire émotionnel explicite. Une prose qui déplace délibérément la charge affective sur un détail concret sans jamais nommer l'émotion (procédé fréquent dans les récits de deuil ou de violence retenue) obtiendra un score bas, quelle que soit la charge réelle du texte — ce n'est pas un défaut de calibrage mais une limite structurelle d'une détection lexicale sans compréhension sémantique. Même un LLM aurait du mal à détecter ce genre de décallage.

<a id="discursivite_score"></a>
##### **Discursif** / Immersif (discursivite_score)
Score fondé sur la densité des [connecteurs logiques](#logical_connector_ratio) et argumentatifs, la part de [noms abstraits](#abstract_noun_ratio) et le [présent gnomique](#gnomic_present_ratio). Une valeur élevée indique davantage de commentaire, de généralisation ou d'argumentation ; une valeur faible correspond à une scène plus directement vécue ou décrite.

**Limite :** les trois composantes reposent sur des lexiques et des patrons syntaxiques fixes ; un texte qui argumente sans connecteurs explicites (par juxtaposition, par exemple) ou qui généralise sans passer par le présent gnomique passera sous le radar de cette mesure.


### Lecture des résultats

<a id="note_dispersion"></a>
##### Dispersion (note_dispersion)
Indique à quel point une mesure diffèrent pour les œuvres du corpus. Une dispersion σ est jugée significative si elle est supérieure à 5 %, ce qui implique que les œuvres montrent des caractères différents.

Pour les mesures exprimées autrement qu'en pourcentage (mots, caractères, profondeur, ratio numérique…), les valeurs deviennent leur écart relatif à la moyenne du corpus : `(valeur − moyenne) / |moyenne| × 100`. D'une manière générale, si l’écart entre la plus petite et la plus grande valeur est inférieur à 5 %, σ est fixé à 0 : pas de variation significative, mesure non expoitable.

<a id="note_coverage"></a>
##### Couverture stylistique (note_coverage)

Surface sur le graphique radar en fonction des valeurs affichées. C'est une signature stylistique et non un critère de qualité.

Pour rendre les axes comparables, le radar établit ses repères une seule fois sur tout le corpus, jamais sur la sélection affichée. La valeur est d'abord rapportée au maximum du corpus (`valeur / maximum`) sans soustraire le minimum, puis transformée par une courbe logarithmique `log(1 + 4x) / log(5)`. La plus petite valeur conserve ainsi sa proportion réelle au lieu d'être artificiellement ramenée à 0 %. Cette courbe continue étale les valeurs basses et ralentit progressivement l'approche de 100 %, sans supprimer ni saturer brutalement aucune œuvre. La transformation s'applique aux coordonnées du radar et au calcul de sa surface, sans modifier les valeurs brutes des tableaux.

Ce tassemment modère l'influence des choix stylistiques extrêmes, comme les phrases très longues qui mécaniquement tirent beaucoup d'indices à la hausse.

<a id="note_singularity"></a>
##### Singularité (note_singularity)
Distance de Burrows calculée uniquement sur les mesures stylistiques dont la [dispersion](#note_dispersion) atteint au moins 5 % parmi toutes les œuvres du corpus choisi. Ce filtrage porte sur le corpus complet et ne dépend jamais des œuvres ou auteurs sélectionnés dans l’interface. Chaque mesure retenue est d’abord centrée et réduite sur l’ensemble du corpus ; la distance entre deux œuvres est la moyenne des écarts absolus entre leurs z-scores. Le graphique affiche, pour chaque œuvre ou auteur sélectionné, la distance à son voisin le plus proche. Une valeur faible indique une proximité statistique, pas une identité d’auteur ni une preuve d’influence.

<a id="note_mds"></a>
##### Carte stylistique MDS (note_mds)
Projection en deux dimensions des distances de Burrows calculées sur les seules mesures dont la [dispersion](#note_dispersion) atteint au moins 5 % parmi toutes les œuvres du corpus choisi, indépendamment de la sélection affichée. Les œuvres proches dans la carte sont proches dans cet espace multidimensionnel ; les axes de la projection n’ont pas de signification littéraire propre. Le stress indique la déformation introduite par la réduction à deux dimensions : plus il est faible, plus la carte respecte les distances originales.

<a id="note_neighborhood"></a>
##### Voisinage stylistique (note_neighborhood)
Pour l’œuvre choisie, les œuvres les plus proches sont classées par percentile décroissant. L’axe affiche le percentile de proximité dans toutes les distances du corpus : 90 % signifie que l’œuvre est plus proche que 90 % des paires comparées. Le titre du tableau donne directement le nombre de voisins par auteur. Les couleurs identifient les auteurs ; l’auteur de référence est affiché en couleur pleine afin que le nombre de voisins du même auteur soit immédiatement lisible. Une œuvre peut être épinglée pour apparaître en ligne supplémentaire, avec son rang réel dans le classement. Ces repères sont descriptifs et ne constituent pas une preuve d’attribution.

Mathématiquement, chaque œuvre est représentée par le vecteur des mesures dont la [dispersion](#note_dispersion) atteint au moins 5 % sur le corpus complet, jamais sur la seule sélection affichée. Pour chaque mesure retenue `j`, on calcule sur toutes les œuvres du corpus la moyenne `μⱼ` et l’écart-type `σⱼ`, puis le score centré-réduit `zⱼ = (xⱼ − μⱼ) / σⱼ`. La distance entre deux œuvres `A` et `B` est la moyenne des écarts absolus sur les `p` mesures : `d(A,B) = (1/p) × Σ |zAⱼ − zBⱼ|`. Les voisins sont ensuite triés par distance croissante. Le percentile affiché est la proportion des distances du corpus qui sont supérieures à cette distance, multipliée par 100.

### Mesures

Tentent de capturer les diverses caractéristiques d'un texte.



#### Ponctuation

<a id="punctuation_ratio"></a>
##### **Densité de ponctuations** / Sparsité de ponctuations (punctuation_ratio)
[Nombre total de signes de ponctuation](#punctuation_mark_count) divisé par le [nombre de mots](#word_count).

<a id="punctuation_diversity"></a>
##### **Complexité de ponctuation** / Simplicité de ponctuation (punctuation_diversity)
Entropie de Shannon de la répartition entre les dix comptages élémentaires : [points](#period_count), [virgules](#comma_count), [deux-points](#colon_count), [points-virgules](#semicolons_count), [points d’exclamation](#exclamation_point_count), [points d’interrogation](#question_mark_count), [points de suspension](#suspention_point_count), [tirets](#dash_count), [parenthèses](#parenthesis_count) et [guillemets](#quote_mark_count). L’entropie est divisée par `log₂(10)`. Une valeur faible indique qu’un petit nombre de familles domine ; 100 % implique un emploi parfaitement équilibré des dix familles.

<a id="punctuation_variety_score"></a>
##### Densité de ponctuation savante (punctuation_variety_score)
Somme du [nombre de points-virgules](#semicolons_count), du [nombre de deux-points](#colon_count) et du [nombre de tirets](#dash_count), divisée par le [nombre de phrases](#sentence_count).



#### Syntaxe et grammaire

<a id="structural_diversity"></a>
##### **Diversité syntaxique** / Régularité syntaxique (structural_diversity)
Chaque phrase est d’abord transformée en propositions simplifiées, par exemple `SUJET VERBE COMPLÉMENT` ou `PROPOSITION_SUBORDONNÉE`. Les déterminants et prépositions n'ont pas de rôles. Les virgules et les points sont conservés dans les propositions ordinaires. Les répétitions internes sont comptées : une phrase peut ainsi devenir `SUJET VERBE COMPLÉMENT + 5 PROPOSITIONS_SUBORDONNÉES`.

Deux phrases sont comparées en combinant deux distances : 75 % pour la différence entre les proportions de leurs constructions et 25 % pour la différence entre leurs nombres d’occurrences. Cette distance est ensuite pondérée par la quantité d’information disponible : le poids augmente avec le nombre cumulé de propositions et atteint son maximum à douze. Deux phrases très courtes ne peuvent donc pas créer seules une opposition maximale. À l’inverse, cinq subordonnées identiques apportent moins de diversité que cinq constructions différentes. La valeur finale est la moyenne des distances entre toutes les paires de phrases, de 0 à 100 %.

<a id="sentence_start_diversity"></a>
##### **Diversité des débuts de phrase** / Régularité des débuts de phrase (sentence_start_diversity)
Utilise exactement les signatures déjà produites pour la [diversité syntaxique](#structural_diversity), puis ne conserve que leur première unité. Cette unité s’arrête à la première ponctuation conservée dans la signature ou à l’ouverture d’une proposition subordonnée.

La dispersion est calculée avec l’indice de Gini-Simpson corrigé pour un échantillon fini : `1 − nombre de paires identiques / nombre total de paires`. Elle représente donc la probabilité que deux phrases distinctes choisies au hasard commencent par deux structures différentes. Une valeur de 85 % signifie que 85 % des paires ont des débuts différents et que 15 % ont le même début ; elle ne signifie pas que 85 % des phrases possèdent un début unique.

Pour donner un ordre de grandeur plus intuitif, `1 / (1 − dispersion)` fournit le nombre effectif de structures également fréquentes qui produirait la même dispersion : 85 % équivaut ainsi à environ 6,7 structures équilibrées. Cela ne signifie pas qu’un début se répète toutes les sept phrases, car cette mesure ne tient pas compte de leur ordre dans le texte. 0 % signifie que toutes les phrases commencent de la même manière ; une valeur proche de 100 % indique des débuts très dispersés. Le nombre de structures possibles n’est pas fixé à l’avance.

<a id="sentence_start_recurrence_distance"></a>
##### **Distance de répétition des débuts de phrase** / Proximité des répétitions de débuts (sentence_start_recurrence_distance)
Pour chaque structure de début déjà rencontrée, compte le nombre de phrases écoulées depuis son occurrence précédente, puis calcule la moyenne de ces écarts sur tout le document. L’unité est la **phrase** : une valeur de 7 signifie qu’en moyenne une structure récurrente réapparaît sept phrases après son emploi précédent. Les structures employées une seule fois n’entrent pas dans cette moyenne. Contrairement à la [diversité des débuts de phrase](#sentence_start_diversity), cette mesure tient donc compte de l’ordre du texte et distingue les répétitions rapprochées des reprises espacées.

<a id="structural_rhythm"></a>
##### **Alternance structurelle** / Régularité structurelle (structural_rhythm)
Compare chaque structure de phrase à la suivante dans l’ordre du texte. La distance d’édition compte les rôles qu’il faudrait ajouter, supprimer ou remplacer pour passer d’un patron à l’autre, puis divise ce nombre par la longueur du patron le plus long. Le résultat final est la moyenne de ces distances. 0 % signifie que les mêmes patrons se succèdent ; une valeur élevée indique des changements structurels fréquents.

<a id="noun_verb_ratio"></a>
##### Style nominal / **Style verbal** (noun_verb_ratio)
[Nombre de noms communs](#common_noun_count) et de [noms propres](#proper_noun_count), divisé par le [nombre de verbes du profil grammatical](#grammatical_verb_count). Une valeur de 2 indique deux noms pour un verbe.

Un ratio élevé traduit un style nominal : le texte s'appuie sur des substantifs plutôt que sur des actions, souvent au prix d'une syntaxe plus statique — descriptions, énumérations, écriture administrative ou théorique, phrases qui exposent plutôt qu'elles ne racontent. À l'inverse, un ratio bas traduit un style verbal : le texte progresse par l'action, les procès, les enchaînements d'événements — un rythme plus narratif et dynamique, où les choses se passent plutôt qu'elles ne sont.

<a id="function_word_ratio"></a>
##### Densité grammaticale / **Densité lexicale** (function_word_ratio)
[Nombre de mots grammaticaux](#function_word_count) divisé par le [nombre de mots](#word_count).

Une valeur élevée signifie que le texte s'appuie beaucoup sur le matériel grammatical (déterminants, pronoms, prépositions, conjonctions, interjections) — souvent des phrases courtes, un style oral ou fluide. Une valeur basse signifie que le texte est porté par les mots pleins (noms, verbes, adjectifs, adverbes) — style plus dense, informatif ou nominal.

<a id="noun_ratio"></a>
##### Densité des noms / Sparcité des noms (noun_ratio)
Somme des [noms communs](#common_noun_count) et [noms propres](#proper_noun_count), divisée par le [total du profil grammatical](#grammatical_token_count).

<a id="verb_ratio"></a>
##### Densité des Verbes / Sparcité des verbes (verb_ratio)
[Nombre de verbes du profil grammatical](#grammatical_verb_count) divisé par le [total du profil grammatical](#grammatical_token_count).

<a id="adjective_ratio"></a>
##### Densité des adjectifs / Sparcité des adjectifs (adjective_ratio)
[Nombre d’adjectifs](#adjective_count) divisé par le [total du profil grammatical](#grammatical_token_count).

<a id="adverb_ratio"></a>
##### Densité des adverbes / Sparcité des adverbes (adverb_ratio)
[Nombre d’adverbes](#adverb_count) divisé par le [total du profil grammatical](#grammatical_token_count).

<a id="relative_clause_ratio"></a>
##### **Densité de relatives** / Sparcité de relatives (relative_clause_ratio)
Nombre de dépendances de proposition relative (`acl:relcl`) reconnues par spaCy, divisé par le [nombre de phrases](#sentence_count). Une phrase peut contenir plusieurs relatives, la valeur peut donc dépasser 100 %. Les autres subordonnées sont mesurées séparément par `subordinate_clause_ratio`.

<a id="nominal_sentence_ratio"></a>
##### Densité de phrases nominales / Sparcité de phrases nominales (nominal_sentence_ratio)
Part des [phrases nominales](#nominal_sentence_count) / [nombre de phrases](#sentence_count). Les infinitifs et participes isolés ne suffisent pas à rendre la phrase verbale. La mesure repère notamment des ruptures comme « Un cauchemar. Encore un. ».

<a id="active_voice_ratio"></a>
##### **Densité de voix active** / Densité de voix passive (active_voice_ratio)
[Nombre de phrases actives](#active_sentence_count) divisé par le [nombre de phrases](#sentence_count).

<a id="average_syntactic_depth"></a>
##### **Complexité syntaxique** / Minimalisme syntaxique (average_syntactic_depth)
Mesure la complexité hiérarchique des phrases reconnue par spaCy. Plus des groupes et propositions sont emboîtés les uns dans les autres, plus les mots les plus éloignés nécessitent de relations pour rejoindre le verbe principal, et plus la profondeur augmente.

L'idée : une phrase simple (« Le chat dort ») a une profondeur faible — un seul niveau entre le mot et le verbe. Une phrase à subordonnées empilées (« Le chat que le voisin, qui venait d'emménager, avait recueilli dormait ») a une profondeur élevée — plusieurs relations à traverser pour remonter jusqu'au verbe principal.

<a id="structural_repetition_rate"></a>
##### Répétition des structures (structural_repetition_rate)
Part des signatures syntaxiques de phrases déjà rencontrées dans le texte.

<a id="subordinate_clause_ratio"></a>
##### Densité de subordonnées (subordinate_clause_ratio)
[Nombre de propositions subordonnées](#subordinate_clause_count) divisé par le [nombre de phrases](#sentence_count). Une phrase contenant plusieurs subordonnées contribue plusieurs fois au numérateur ; la valeur peut donc dépasser 100 %.

<a id="common_noun_ratio"></a>
##### Part de noms communs (common_noun_ratio)
Part des [noms communs](#common_noun_count) / [nombre de mots](#word_count).

<a id="proper_noun_ratio"></a>
##### Part des noms propres (proper_noun_ratio)
Part des [noms propres](#proper_noun_count) / [nombre de mots](#word_count).

<a id="avg_modifiers_per_noun"></a>
##### **Modificateurs par nom** (avg_modifiers_per_noun)
[Nombre de modificateurs nominaux](#noun_modifier_count) divisé par le [nombre de noms analysés](#analyzed_noun_count).

<a id="heavily_modified_noun_ratio"></a>
##### **Noms fortement modifiés** (heavily_modified_noun_ratio)
[Nombre de noms fortement modifiés](#heavily_modified_noun_count) divisé par le [nombre de noms analysés](#analyzed_noun_count).

<a id="adjective_chain_ratio"></a>
##### **Chaînes adjectivales** (adjective_chain_ratio)
[Nombre de chaînes d’adjectifs coordonnées](#adjective_chain_count) divisé par le [nombre de phrases](#sentence_count).

<a id="avg_adjective_chain_length"></a>
##### **Longueur des chaînes adjectivales** (avg_adjective_chain_length)
[Nombre d’adjectifs appartenant aux chaînes](#adjective_in_chain_count) divisé par le [nombre de chaînes adjectivales](#adjective_chain_count).

<a id="incise_density"></a>
##### Densité d'incises (incise_density)
[Nombre de phrases contenant une incise](#incise_count) divisé par le [nombre de phrases](#sentence_count).

<a id="coordination_accumulation_ratio"></a>
##### Taux d'accumulation coordonnée (coordination_accumulation_ratio)
[Nombre de phrases contenant une accumulation coordonnée](#coordination_accumulation_count) divisé par le [nombre de phrases](#sentence_count).

<a id="right_branching_depth"></a>
##### Profondeur d'expansion finale (right_branching_depth)
Pour chaque phrase, le dernier mot non ponctué est repéré, puis le programme compte le nombre de liens de dépendance syntaxique à remonter pour atteindre la racine de la phrase. Le résultat est la moyenne de ces nombres sur toutes les phrases. Son unité est donc le **nombre moyen de liens syntaxiques**, et non un pourcentage. Par exemple, si le dernier mot dépend directement du verbe principal, sa profondeur vaut 1 ; s’il dépend d’un mot qui dépend lui-même du verbe principal, elle vaut 2. Une valeur élevée indique que les fins de phrase sont souvent intégrées à des constructions syntaxiques emboîtées.



#### Lexique et répétitions

<a id="local_repetition_ratio"></a>
##### Répétion locale / **Renouvellement lexical local** (local_repetition_ratio)
[Nombre local de répétitions](#local_repetition_count) divisé par le [nombre de mots analysés pour les répétitions](#repetition_word_count). Tout le document est parcouru par blocs successifs de 1 000 mots, y compris le dernier bloc incomplet ; le calcul ne s’arrête pas aux 1 000 premiers mots.

<a id="global_repetition_ratio"></a>
##### Répétition globale / **Renouvellement lexical global** (global_repetition_ratio)
[Nombre global de répétitions lexicales](#global_repetition_count) divisé par le [nombre de mots analysés pour les répétitions](#repetition_word_count). L’historique couvre ici le document entier : toute nouvelle occurrence d’un lemme déjà rencontré est comptée, quelle que soit la distance qui les sépare.

<a id="local_phonetic_repetition_ratio"></a>
##### Répétition sonore locale / Diversité sonore locale (local_phonetic_repetition_ratio)
[Nombre local de répétitions sonores](#local_phonetic_repetition_count) divisé par le [nombre de mots analysés pour les répétitions](#repetition_word_count). Tout le document est parcouru par blocs successifs de 1 000 mots, y compris le dernier bloc incomplet ; le calcul ne s’arrête pas aux 1 000 premiers mots.

<a id="global_phonetic_repetition_ratio"></a>
##### Répétition sonore globale / Diversité sonore globale (global_phonetic_repetition_ratio)
[Nombre global de répétitions sonores](#global_phonetic_repetition_count) divisé par le [nombre de mots analysés pour les répétitions](#repetition_word_count).

<a id="absolute_repetition_rate"></a>
##### Redondance lexicale brute / Renouvellement lexical brut (absolute_repetition_rate)
[Nombre de répétitions lexicales brutes](#absolute_repetition_count) divisé par le [nombre de mots analysés pour les répétitions](#repetition_word_count). Contrairement aux répétitions lexicales locales et globales filtrées, le numérateur conserve les mots-outils. La mesure inclut donc les répétitions grammaticales ordinaires du français et sera naturellement beaucoup plus élevée.

<a id="trigram_repetition"></a>
##### Redondance des trigrammes / Renouvellement des trigrammes (trigram_repetition)
Un trigramme est une suite de trois lemmes consécutifs. Sur le document total, chaque mot est d’abord remplacé par son lemme contextuel : `marche`, `marches` et `marchent` employés comme verbes deviennent ainsi `marcher`, tandis que le nom dans `la marche` reste `marche`. spaCy désambiguïse la catégorie grâce à la phrase ; Morphalou sert de repli lorsque cette analyse contextuelle est indisponible. Le programme compte les trigrammes distincts présents plus d’une fois, puis divise ce nombre par le nombre total de trigrammes distincts. Il s’agit donc d’une proportion de types répétés, calculée d’un seul bloc sur toute l’œuvre.

<a id="hapax_ratio"></a>
##### **Taux d'hapax** / Taux de récurrence (hapax_ratio)
[Nombre de lemmes hapax](#hapax_count) divisé par le [nombre de lemmes lexicaux distincts](#unique_lemma_count).

Un taux élevé signifie que le texte introduit beaucoup de mots qu'il n'utilise ensuite plus jamais (vocabulaire riche et non répété, parfois signe d'un style très varié ou au contraire de rareté statistique) ; un taux bas signifie que le vocabulaire lexical est concentré sur peu de lemmes, réemployés souvent.

<a id="lemma_diversity_ratio"></a>
##### Diversité des lemmes (lemma_diversity_ratio)
[Nombre de lemmes distincts](#unique_lemma_count) divisé par le [nombre total de mots](#word_count) du document. Les flexions d’un même lemme sont regroupées. La valeur est comprise entre 0 et 1.

<a id="type_token_ratio"></a>
##### Diversité lexicale globale (type_token_ratio)
[Nombre de formes graphiques distinctes](#distinct_form_count) divisé par le [nombre total de mots](#word_count) du document. Une valeur élevée indique un vocabulaire peu répété ; elle dépend fortement de la longueur du texte.

<a id="moving_type_token_ratio"></a>
##### Diversité lexicale mobile (moving_type_token_ratio)
Dans chaque bloc successif de 1 000 mots, le nombre de formes graphiques distinctes est divisé par le nombre de mots du bloc. La valeur du document est la moyenne des résultats de tous les blocs, y compris le dernier bloc incomplet ; le calcul ne s’arrête jamais au premier bloc.

<a id="global_lemma_richness"></a>
##### Richesse globale des lemmes (global_lemma_richness)
[Nombre de lemmes distincts](#unique_lemma_count) divisé par le [nombre de mots lexicaux](#lexical_word_count) du document.

<a id="lemma_richness"></a>
##### Richesse locale des lemmes (lemma_richness)
Dans chaque bloc successif de 1 000 mots, le nombre de lemmes distincts est divisé par le nombre de mots lexicaux du bloc. La valeur du document est la moyenne des résultats de tous les blocs, y compris le dernier bloc incomplet ; le calcul ne s’arrête jamais au premier bloc.

<a id="morphalou_coverage"></a>
##### Couverture Morphalou (morphalou_coverage)
[Nombre de formes lexicales reconnues par Morphalou](#morphalou_recognized_count) divisé par le [nombre de mots lexicaux](#lexical_word_count).

<a id="lexical_rarity_score"></a>
##### **Rareté lexicale** (lexical_rarity_score)
Moyenne de `-log10` des fréquences Lexique383. Une valeur élevée indique un vocabulaire moins fréquent ; Lexique383 ne distingue pas le vocabulaire littéraire du vocabulaire technique.



#### Rythme, longueurs et lisibilité

<a id="burstiness"></a>
##### **Diversité locale de longueur de phrase** / Uniformité locale de longueur de phrase (burstiness)
Moyenne des différences absolues de longueur en mots entre chaque paire de phrases consécutives, divisée par la longueur moyenne des phrases. Cette normalisation rend comparables les textes aux phrases globalement courtes ou longues.

<a id="gzip_compression_ratio"></a>
##### **Compressibilité gzip** / Incompressibilité gzip (gzip_compression_ratio)
[Nombre d’octets après compression gzip](#gzip_byte_count) divisé par le [nombre d’octets UTF-8](#utf8_byte_count). Une valeur basse indique un texte plus prévisible et plus compressible.

<a id="avg_word_length"></a>
##### Longueur moyenne des mots (caractères) (avg_word_length)
Somme des longueurs des mots en caractères divisée par le [nombre de mots](#word_count). La somme est un intermédiaire de calcul, pas une mesure exposée.

<a id="avg_sentence_length"></a>
##### Longueur moyenne des phrases (mots) (avg_sentence_length)
Somme des nombres de mots relevés phrase par phrase, divisée par le [nombre de phrases](#sentence_count).

<a id="median_sentence_length"></a>
##### Longueur médiane des phrases (mots) (median_sentence_length)
Médiane de la distribution ordonnée du nombre de mots par [phrase](#sentence_count). Cette statistique de rang ne peut pas être reconstruite à partir d’une simple somme.

<a id="sentence_length_p10"></a>
##### Longueur P10 des phrases (mots) (sentence_length_p10)
Interpolation au rang 10 % de la distribution ordonnée du nombre de mots par phrase.

<a id="sentence_length_p90"></a>
##### Longueur P90 des phrases (mots) (sentence_length_p90)
Interpolation au rang 90 % de la distribution ordonnée du nombre de mots par phrase.

<a id="paragraph_length_std_dev"></a>
##### Écart-type des paragraphes (paragraph_length_std_dev)
Écart-type du nombre de mots par [paragraphe](#paragraph_count) sur l’ensemble du document.

<a id="sentence_length_amplitude"></a>
##### Amplitude des longueurs de phrase (sentence_length_amplitude)
Différence entre la [longueur P90](#sentence_length_p90) et la [longueur P10](#sentence_length_p10). Cette statistique dérive de deux mesures d’analyse, pas de comptages bruts supplémentaires.

<a id="sentence_length_std_dev"></a>
##### **Diversité de longueurs de phrase** / Uniformité des longueurs de phrase (sentence_length_std_dev)
Écart-type du nombre de mots par [phrase](#sentence_count) sur l’ensemble du document. Une valeur élevée indique une alternance plus forte entre phrases courtes et longues.

<a id="avg_paragraph_length"></a>
##### Longueur moyenne des paragraphes (avg_paragraph_length)
Somme des nombres de mots relevés paragraphe par paragraphe, divisée par le [nombre de paragraphes](#paragraph_count).

<a id="flesch"></a>
##### Lisibilité de Flesch (flesch)
Indice français calculé avec le [nombre de mots](#word_count), le [nombre de phrases](#sentence_count) et le [nombre de syllabes](#syllable_count) : `207 − 1,015 × mots/phrases − 73,6 × syllabes/mots`.

#### Narration, temps et registre

<a id="metaphorical_comme_ratio"></a>
##### Densité de métaphores / Sparcité de métaphores (metaphorical_comme_ratio)
[Nombre de phrases contenant une comparaison](#methaphore_count) divisé par le [nombre de phrases](#sentence_count).

<a id="present_participle_ratio"></a>
##### **Densité de participes présents** / Sparcité de participes présents (present_participle_ratio)
[Nombre de participes présents](#present_participe_count) divisé par le [nombre de mots](#word_count).

<a id="past_participle_ratio"></a>
##### **Densité de participes passés** / Sparcité de participes passés (past_participle_ratio)
[Nombre de participes passés](#past_participe_count) divisé par le [nombre de mots](#word_count).

<a id="simple_past_ratio"></a>
##### **Passé simple** / Présence du passé simple (simple_past_ratio)
[Nombre de passés simples](#simple_past_count) divisé par le [nombre de verbes narratifs](#narrative_verb_count).

<a id="literary_subjunctive_ratio"></a>
##### **Subjonctif imparfait ou plus-que-parfait** / Subjonctif littéraire (literary_subjunctive_ratio)
[Nombre de subjonctifs littéraires](#subjonctive_count) divisé par le [nombre de verbes narratifs](#narrative_verb_count).

<a id="negation_completeness_ratio"></a>
##### **Négations complètes** / Négations sans « ne » (negation_completeness_ratio)
[Nombre de négations avec « ne »](#verb_negation_count) divisé par le [nombre de négations](#negation_count).

<a id="periphrastic_future_ratio"></a>
##### **Futur périphrastique** / Futur simple (periphrastic_future_ratio)
[Nombre de futurs périphrastiques](#va_count) divisé par la somme des [futurs périphrastiques](#va_count) et des [futurs simples](#future_count).

<a id="oral_familiarity_ratio"></a>
##### **Familiarité orale** / Registre soutenu (oral_familiarity_ratio)
[Nombre de marqueurs de familiarité orale](#familiarity_marker_count) rapporté au [nombre de mots](#word_count), pour 100 mots.

<a id="action_verb_ratio"></a>
##### **Verbes d’action** (action_verb_ratio)
[Nombre de verbes d’action](#active_verb_count) divisé par le [nombre de verbes narratifs](#narrative_verb_count).

<a id="temporal_connector_ratio"></a>
##### **Connecteurs temporels** (temporal_connector_ratio)
[Nombre de connecteurs temporels](#temporal_connector_count) rapporté au [nombre de phrases](#sentence_count), pour 100 phrases.

<a id="personal_subject_ratio"></a>
##### **Sujets personnels** (personal_subject_ratio)
[Nombre de sujets personnels](#personal_subject_count) divisé par le [nombre de sujets classables](#classifiable_subject_count).

<!-- Note conservée pour référence historique : la mesure n’est plus calculée ni exposée. -->

<a id="narrative_past_ratio"></a>
##### **Passé narratif** (narrative_past_ratio)
[Nombre de verbes narratifs au passé](#narrative_past_count) divisé par le [nombre de verbes narratifs](#narrative_verb_count).

<a id="dialogue_ratio"></a>
##### **Dialogue** (dialogue_ratio)
[Nombre de mots en dialogue](#dialog_word_count) divisé par le [nombre de mots](#word_count).

<a id="proper_noun_density"></a>
##### Densité de noms propres (proper_noun_density)
[Nombre de noms propres](#proper_noun_count) divisé par le [nombre de tokens lexicaux spaCy](#lexical_token_count).

<a id="concrete_noun_ratio"></a>
##### Noms concrets (concrete_noun_ratio)
[Nombre de noms concrets](#concrate_noun_count) divisé par le [nombre de noms communs](#common_noun_count).

<a id="tense_shift_rate"></a>
##### Taux de rupture temporelle (tense_shift_rate)
[Nombre de ruptures temporelles](#tense_shift_count) divisé par le [nombre de transitions temporelles analysables](#tense_transition_count).

<a id="scene_summary_ratio"></a>
##### Taux de marqueurs de sommaire (scene_summary_ratio)
[Nombre de phrases contenant un marqueur de sommaire](#summary_sentence_count) divisé par le [nombre de phrases](#sentence_count).

<a id="negation_ratio"></a>
##### **Négativité** / Positivité (negation_ratio)
[Nombre de phrases négatives](#negative_sentence_count) divisé par le [nombre de phrases](#sentence_count).

<a id="ellipsis_ratio"></a>
##### Densité de points de suspension (ellipsis_ratio)
[Nombre de points de suspension](#suspention_point_count) divisé par le [nombre de phrases](#sentence_count).

<a id="question_mark_ratio"></a>
##### Points d'interrogation (question_mark_ratio)
[Nombre total de points d’interrogation](#question_mark_count) rapporté [au nombre de phrases](#sentence_count).

<a id="exclamation_ratio"></a>
##### Exclamations (exclamation_ratio)
[Nombre de points d’exclamation](#exclamation_point_count) rapporté [au nombre de phrases](#sentence_count). Cette mesure repère la ponctuation expressive, sans interpréter le contenu.

<a id="exclamative_construction_ratio"></a>
##### Constructions exclamatives (exclamative_construction_ratio)
[Nombre de constructions exclamatives](#exclamative_sentence_count) divisé par le [nombre de phrases](#sentence_count).

#### Émotions

<a id="emotion_word_ratio"></a>
##### Mots émotionnels (emotion_word_ratio)
[Nombre de marqueurs émotionnels](#emotion_word_count) divisé par le [nombre de lemmes](#lemma_count).

<a id="emotion_sentence_ratio"></a>
##### Phrases à caractère émotionnel (emotion_sentence_ratio)
[Nombre de phrases émotionnelles](#emotion_sentence_count) divisé par le [nombre de phrases](#sentence_count).

<a id="intensifier_adjective_ratio"></a>
##### Intensificateurs devant adjectif (intensifier_adjective_ratio)
[Nombre d’adjectifs intensifiés](#intensified_adjective_count) divisé par le [nombre d’adjectifs](#adjective_count).

<a id="emotion_intensification_ratio"></a>
##### Intensification émotionnelle (emotion_intensification_ratio)
Somme des huit comptages d’occurrences émotionnelles intensifiées — de la [joie intensifiée](#joy_intensified_emotion_count) aux [manifestations somatiques intensifiées](#somatic_intensified_emotion_count) — divisée par la somme des huit [comptages émotionnels](#joy_emotion_count).

<a id="joy_emotion_ratio"></a>
##### Joie (joy_emotion_ratio)
[Nombre d’occurrences de joie](#joy_emotion_count) divisé par la somme des huit comptages émotionnels.

<a id="sadness_emotion_ratio"></a>
##### Tristesse (sadness_emotion_ratio)
[Nombre d’occurrences de tristesse](#sadness_emotion_count) divisé par la somme des huit comptages émotionnels.

<a id="fear_emotion_ratio"></a>
##### Peur (fear_emotion_ratio)
[Nombre d’occurrences de peur](#fear_emotion_count) divisé par la somme des huit comptages émotionnels.

<a id="anger_emotion_ratio"></a>
##### Colère (anger_emotion_ratio)
[Nombre d’occurrences de colère](#anger_emotion_count) divisé par la somme des huit comptages émotionnels.

<a id="surprise_emotion_ratio"></a>
##### Surprise (surprise_emotion_ratio)
[Nombre d’occurrences de surprise](#surprise_emotion_count) divisé par la somme des huit comptages émotionnels.

<a id="disgust_emotion_ratio"></a>
##### Dégoût (disgust_emotion_ratio)
[Nombre d’occurrences de dégoût](#disgust_emotion_count) divisé par la somme des huit comptages émotionnels.

<a id="contempt_emotion_ratio"></a>
##### Mépris (contempt_emotion_ratio)
[Nombre d’occurrences de mépris](#contempt_emotion_count) divisé par la somme des huit comptages émotionnels.

<a id="somatic_emotion_ratio"></a>
##### Manifestations somatiques (somatic_emotion_ratio)
[Nombre de manifestations somatiques](#somatic_emotion_count) divisé par la somme des huit comptages émotionnels.

<a id="emotional_category_entropy"></a>
##### Entropie émotionnelle (emotional_category_entropy)
Entropie de Shannon brute, en bits, calculée sur les huit comptages allant de la [joie](#joy_emotion_count) aux [manifestations somatiques](#somatic_emotion_count). Une valeur proche de 0 indique qu’un seul registre domine ; le maximum théorique de 3 bits correspond à huit registres mobilisés de façon équilibrée. La mesure est indépendante du nombre total d’occurrences.

#### Discours et modalité

<a id="logical_connector_ratio"></a>
##### Connecteurs logiques (logical_connector_ratio)
[Nombre de connecteurs logiques ou argumentatifs](#logical_connector_count) rapporté au [nombre de phrases](#sentence_count). Les marqueurs sont définis dans `assets/dictionnaires/logical-connectors.txt`.

<a id="abstract_noun_ratio"></a>
##### Noms abstraits (abstract_noun_ratio)
[Nombre de noms abstraits](#abstract_noun_count) divisé par le [nombre de noms communs](#common_noun_count).

<a id="gnomic_present_ratio"></a>
##### Ratio de présents gnomiques (gnomic_present_ratio)
[Nombre de présents gnomiques](#gnomic_present_count) divisé par le [nombre de verbes conjugués](#conjugue_verb_count).

<a id="modal_generalization_ratio"></a>
##### Taux de modalité généralisante (modal_generalization_ratio)
[Nombre de modaux généralisants](#modal_generalization_count) divisé par le [nombre total de verbes](#verb_count).

### Données brutes

Ces mesures, indiquées en valeurs absolus, décrivent les éléments linguistiques élémentaires des documents.

<a id="word_count"></a>
##### Mots (word_count)
Nombre total de mots relevés dans le document analysé.

<a id="lexical_word_count"></a>
##### Mots lexicaux (lexical_word_count)
Nombre de mots lexicaux retenus après exclusion des mots-outils.

<a id="distinct_form_count"></a>
##### Formes graphiques distinctes (distinct_form_count)
Nombre de graphies différentes parmi tous les [mots](#word_count) du document, sans regroupement de leurs flexions.

<a id="morphalou_recognized_count"></a>
##### Formes reconnues par Morphalou (morphalou_recognized_count)
Nombre de mots lexicaux dont la forme possède une entrée dans Morphalou.

<a id="sentence_count"></a>
##### Phrases (sentence_count)
Nombre total de phrases relevées dans le document analysé.

<a id="paragraph_count"></a>
##### Paragraphes (paragraph_count)
Nombre total de paragraphes relevés dans le document analysé.

<a id="document_char_count"></a>
##### Caractères (document_char_count)
Nombre total de caractères du document analysé, espaces et retours à la ligne compris.

<a id="utf8_byte_count"></a>
##### Octets UTF-8 (utf8_byte_count)
Taille brute du document en octets après encodage UTF-8. Elle peut dépasser le nombre de caractères, notamment pour les lettres accentuées.

<a id="gzip_byte_count"></a>
##### Octets gzip (gzip_byte_count)
Taille brute en octets du même document compressé avec gzip. L’horodatage de l’archive est fixé à zéro afin que le comptage soit reproductible.

<a id="syllable_count"></a>
##### Syllabes (syllable_count)
Nombre total de syllabes estimées par groupes de voyelles. Chaque mot compte au minimum une syllabe ; ce comptage orthographique est une approximation destinée au calcul de Flesch.

<a id="relative_clause_count"></a>
##### Propositions relatives (relative_clause_count)
Nombre de propositions relatives reconnues par spaCy.

<a id="subordinate_clause_count"></a>
##### Propositions subordonnées (subordinate_clause_count)
Nombre de propositions subordonnées reconnues par spaCy.

<a id="nominal_sentence_count"></a>
##### Phrases nominales (nominal_sentence_count)
Nombre de phrases dans lesquelles spaCy ne trouve aucun verbe conjugué.

<a id="common_noun_count"></a>
##### Noms communs (common_noun_count)
Nombre de noms communs dans la distribution grammaticale calculée par spaCy.

<a id="abstract_noun_count"></a>
##### Noms abstraits (abstract_noun_count)
Un nom est considéré abstrait lorsque sa forme se termine par un suffixe fréquent de nominalisation (`-tion`, `-isme`, `-ité`… voir `assets/dictionnaires/abstract-noun-suffixes.txt`). Il s’agit d’une approximation orthographique : elle peut classer à tort des noms concrets comme « voiture ».

<a id="proper_noun_count"></a>
##### Noms propres (proper_noun_count)
Nombre de noms propres dans la distribution grammaticale calculée par spaCy.

<a id="lemma_count"></a>
##### Lemmes (lemma_count)
Nombre total d’occurrences lexicales après lemmatisation. Chaque occurrence reste comptée, même lorsque plusieurs formes correspondent au même lemme. Par exemple, dans « il marche et elles marchent », les formes « marche » et « marchent » sont toutes deux ramenées à « marcher », mais elles produisent **2 occurrences de lemme**.

<a id="unique_lemma_count"></a>
##### Lemmes distincts (unique_lemma_count)
Nombre de lemmes lexicaux différents, sans compter plusieurs fois leurs occurrences ou leurs variantes conjuguées. Par exemple, dans « il marche et elles marchent », « marche » et « marchent » correspondent toutes deux au lemme « marcher » et produisent donc **1 seul lemme distinct**.

<a id="hapax_count"></a>
##### Lemmes hapax (hapax_count)
Nombre de lemmes lexicaux apparaissant exactement une fois dans le document. Les flexions regroupées sous un même lemme ne constituent pas des hapax différents.

<a id="repetition_word_count"></a>
##### Mots analysés pour les répétitions (repetition_word_count)
Nombre d’occurrences d’au moins deux caractères soumises aux calculs de répétition. Ce total commun sert de dénominateur aux ratios locaux et globaux ; les mots-outils restent dans ce dénominateur, mais ne peuvent pas produire une répétition.

<a id="local_repetition_count"></a>
##### Répétitions locales (local_repetition_count)
Somme des répétitions relevées dans tous les blocs successifs de 1 000 mots du document, y compris le dernier bloc incomplet. Une occurrence est comptée lorsque son lemme a déjà été rencontré dans le même bloc. L’historique est remis à zéro entre deux blocs, mais aucun bloc n’est ignoré. Les flexions d’un même lemme sont regroupées ; les mots-outils sont exclus des répétitions.

<a id="global_repetition_count"></a>
##### Répétitions globales (global_repetition_count)
Nombre d’occurrences dont le lemme a déjà été rencontré plus tôt dans le document entier. Les flexions d’un même lemme sont regroupées ; les mots-outils sont exclus des répétitions. Ce compte est toujours supérieur ou égal au compte local.

<a id="absolute_repetition_count"></a>
##### Répétitions lexicales brutes (absolute_repetition_count)
Nombre d’occurrences dont le lemme a déjà été rencontré plus tôt dans le document entier, mots-outils compris. Les flexions d’un même lemme sont regroupées. Cette donnée est le numérateur brut de la [redondance lexicale brute](#absolute_repetition_rate).

<a id="local_phonetic_repetition_count"></a>
##### Répétitions sonores locales (local_phonetic_repetition_count)
Somme obtenue après parcours de tous les blocs successifs de 1 000 mots du document, y compris le dernier bloc incomplet. Dans chaque bloc, le programme compte les occurrences dont une prononciation partage avec un mot antérieur du même bloc une suite continue d’au moins trois phonèmes couvrant au moins 60 % de la prononciation la plus courte. L’historique est remis à zéro au changement de bloc, mais aucun bloc n’est ignoré. Les mots-outils sont exclus.

<a id="global_phonetic_repetition_count"></a>
##### Répétitions sonores globales (global_phonetic_repetition_count)
Même comptage phonétique sur le document entier : toute occurrence possédant un écho antérieur est comptée, quelle que soit leur distance. Ce compte est toujours supérieur ou égal au compte local.

<a id="verb_count"></a>
##### Verbes (verb_count)
Nombre de tokens reconnus comme verbes ou auxiliaires par spaCy.

<a id="grammatical_verb_count"></a>
##### Verbes du profil grammatical (grammatical_verb_count)
Nombre de verbes finis retenus dans le profil grammatical spaCy.

<a id="grammatical_token_count"></a>
##### Total du profil grammatical (grammatical_token_count)
Somme des noms communs, noms propres, verbes finis, adjectifs et adverbes utilisée comme dénominateur commun des quatre densités grammaticales.

<a id="function_word_count"></a>
##### Mots grammaticaux (function_word_count)
Nombre de mots classés comme déterminants, pronoms, prépositions, conjonctions ou interjections par Morphalou ou par `assets/dictionnaires/function-words.txt`. Les adverbes ne sont pas inclus.

<a id="modal_generalization_count"></a>
##### Modaux généralisants (modal_generalization_count)
Compte les occurrences des verbes de `assets/dictionnaires/modal_verbs.txt` (`devoir`, `pouvoir`, `falloir`) lorsque leur sujet est l’un des pronoms génériques de `assets/dictionnaires/generic-subject-pronouns.txt`. `Falloir` est toujours compté, car ce verbe est impersonnel par construction (« il faut »). La mesure ne tente pas de décider si le pronom « il » d’un autre verbe est impersonnel.

<a id="conjugue_verb_count"></a>
##### Verbes conjugués (conjugue_verb_count)
Nombre de verbes ou auxiliaires portant la marque morphologique d’une forme finie dans tout le document, dialogues compris.

<a id="adjective_count"></a>
##### Adjectifs (adjective_count)
Nombre d’adjectifs reconnus par spaCy.

<a id="intensified_adjective_count"></a>
##### Adjectifs intensifiés (intensified_adjective_count)
Nombre d’adjectifs immédiatement précédés ou syntaxiquement modifiés (`advmod`) par un adverbe d’intensité tel que « si », « tellement », « très », « extrêmement » ou « terriblement ». Un adjectif n’est compté qu’une fois lorsque les deux critères sont satisfaits.

<a id="adverb_count"></a>
##### Adverbes (adverb_count)
Nombre d’adverbes reconnus par spaCy.

<a id="present_participe_count"></a>
##### Participes présents (present_participe_count)
Nombre de formes verbales identifiées par spaCy comme participes présents (`VerbForm=Part`, `Tense=Pres`).

<a id="past_participe_count"></a>
##### Participes passés (past_participe_count)
Nombre de formes verbales identifiées par spaCy comme participes passés (`VerbForm=Part`, `Tense=Past`). Un participe étiqueté comme adjectif n’est pas compté ici.

<a id="simple_past_count"></a>
##### Passés simples (simple_past_count)
Nombre de verbes au passé simple reconnus hors dialogues. Le filtrage des formes ambiguës exige un contexte verbal passé dans la phrase afin de limiter les faux positifs homographes du présent.

<a id="va_count"></a>
##### Futurs périphrastiques (va_count)
Nombre de constructions au futur périphrastique reconnues dans la narration.

<a id="future_count"></a>
##### Futurs simples (future_count)
Nombre de verbes au futur simple reconnus dans la narration.

<a id="subjonctive_count"></a>
##### Subjonctifs (subjonctive_count)
Nombre de subjonctifs imparfaits ou plus-que-parfaits reconnus dans la narration.

<a id="negation_count"></a>
##### Négations (negation_count)
Nombre de marqueurs négatifs reconnus hors dialogues. « ne… que » est exclu.

<a id="verb_negation_count"></a>
##### Négations avec « ne » (verb_negation_count)
Nombre de négations complètes comportant « ne » dans la narration.

<a id="dialog_word_count"></a>
##### Mots en dialogue (dialog_word_count)
Nombre de mots appartenant aux paragraphes dont le premier caractère hors espaces est un tiret cadratin, un tiret demi-cadratin ou un guillemet ouvrant. Le paragraphe entier est alors considéré comme dialogué.

<a id="familiarity_marker_count"></a>
##### Marqueurs de familiarité orale (familiarity_marker_count)
Nombre d’occurrences reconnues dans `assets/dictionnaires/familiarity-markers.txt`. Les marqueurs directs comptent partout ; les marqueurs positionnels seulement avant une ponctuation de fin de proposition.

<a id="active_sentence_count"></a>
##### Phrases actives (active_sentence_count)
Nombre de phrases contenant une construction verbale active et aucune construction passive.

<a id="passive_sentence_count"></a>
##### Phrases passives (passive_sentence_count)
Nombre de phrases contenant une construction passive.

<a id="methaphore_count"></a>
##### Métaphores (methaphore_count)
Nombre de phrases contenant au moins une comparaison reconnue. Le programme distingue les « comme » comparatifs des emplois conjonctifs et utilise aussi `assets/dictionnaires/comparison-markers.txt`. Il repère une forme comparative sans garantir qu’elle constitue sémantiquement une métaphore.

<a id="concrate_noun_count"></a>
##### Noms concrets (concrate_noun_count)
Nombre de noms communs sans suffixe de nominalisation abstraite. Les exceptions de `assets/dictionnaires/concrete-noun-exceptions.txt` sont retirées.

<a id="active_verb_count"></a>
##### Verbes d’action (active_verb_count)
Nombre de verbes narratifs qui ne figurent pas dans `assets/dictionnaires/stative-verbs.txt`. Cette opposition lexicale ne tient pas compte du sens contextuel du verbe.

<a id="narrative_verb_count"></a>
##### Verbes narratifs (narrative_verb_count)
Nombre de verbes conjugués situés hors dialogue.

<a id="narrative_past_count"></a>
##### Verbes narratifs au passé (narrative_past_count)
Nombre de verbes narratifs dont spaCy indique le temps morphologique `Past`.

<a id="gnomic_present_count"></a>
##### Présents gnomiques (gnomic_present_count)
Nombre de verbes finis au présent de l’indicatif dont le sujet grammatical est interprété comme générique, dans tout le document, dialogues compris. Le repérage est heuristique : sont considérés comme génériques les sujets exprimés par un nom commun (« les hommes vieillissent ») ou par l’un des pronoms de `assets/dictionnaires/generic-subject-pronouns.txt`. Les sujets personnels « je », « tu », « il »… ne sont pas comptés. La fonction ne sait toutefois pas distinguer avec certitude un nom commun générique d’un individu situé : « le chien aboie toujours » et « le chien aboie dans la cour » peuvent tous deux être retenus.

<a id="personal_subject_count"></a>
##### Sujets personnels (personal_subject_count)
Nombre de sujets personnels reconnus parmi les sujets classables.

<a id="classifiable_subject_count"></a>
##### Sujets classables (classifiable_subject_count)
Nombre de sujets que l’heuristique peut classer comme personnels ou non personnels. Les noms propres et les pronoms personnels sont classés ; les noms communs et les pronoms ambigus sont laissés de côté. `Il` est considéré non personnel seulement avec une liste restreinte de constructions impersonnelles.

<a id="lexical_token_count"></a>
##### Tokens lexicaux spaCy (lexical_token_count)
Nombre de tokens qui ne sont ni des espaces ni des signes de ponctuation selon spaCy. Ce dénominateur inclut donc davantage d’éléments que le seul nombre de mots alphabétiques.

<a id="tense_shift_count"></a>
##### Ruptures temporelles (tense_shift_count)
Nombre de transitions entre deux paragraphes analysables consécutifs pour lesquelles le temps verbal dominant change. Le temps dominant est celui que spaCy attribue au plus grand nombre de verbes du paragraphe.

<a id="tense_transition_count"></a>
##### Transitions temporelles analysables (tense_transition_count)
Nombre de transitions entre paragraphes consécutifs contenant au moins un verbe porteur d’une indication de temps. Les paragraphes sans temps verbal reconnu sont ignorés.

<a id="summary_sentence_count"></a>
##### Phrases contenant un marqueur de sommaire (summary_sentence_count)
Nombre de phrases contenant au moins un mot ou une expression de `assets/dictionnaires/duration-markers.txt`, par exemple « souvent », « chaque jour » ou « pendant des années ». Ce repérage lexical signale une condensation temporelle possible sans prétendre l’interpréter.

<a id="negative_sentence_count"></a>
##### Phrases négatives (negative_sentence_count)
Nombre de phrases contenant au moins un marqueur de négation, dialogues compris. Une phrase n’est comptée qu’une fois, quel que soit le nombre de marqueurs.

<a id="exclamative_sentence_count"></a>
##### Constructions exclamatives (exclamative_sentence_count)
Nombre de phrases terminées par un point d’exclamation et commençant par « que », « comme », « quel » ou une forme apparentée.

<a id="analyzed_noun_count"></a>
##### Noms analysés pour leurs modificateurs (analyzed_noun_count)
Nombre de noms pour lesquels les modificateurs directs sont comptés.

<a id="noun_modifier_count"></a>
##### Modificateurs nominaux (noun_modifier_count)
Nombre total de modificateurs directement rattachés aux noms : adjectifs, compléments nominaux et propositions relatives selon les dépendances spaCy.

<a id="heavily_modified_noun_count"></a>
##### Noms fortement modifiés (heavily_modified_noun_count)
Nombre de noms portant au moins deux modificateurs directs.

<a id="adjective_chain_count"></a>
##### Chaînes adjectivales (adjective_chain_count)
Nombre de chaînes d’adjectifs coordonnées.

<a id="adjective_in_chain_count"></a>
##### Adjectifs dans les chaînes (adjective_in_chain_count)
Nombre total d’adjectifs appartenant aux chaînes adjectivales coordonnées.

<a id="incise_count"></a>
##### Phrases avec incise (incise_count)
Nombre de phrases contenant au moins une insertion qui interrompt la construction principale. Le programme reconnaît notamment une précision détachée (« Paul, mon voisin, arrive »), une relative explicative (« Paul, qui habite ici, arrive »), une proposition circonstancielle détachée (« Paul, sachant cela, partit ») ou une remarque autonome insérée dans la phrase. Ces constructions sont retenues lorsque spaCy les identifie et qu’une virgule les introduit. Le programme compte aussi les passages encadrés par des parenthèses ou par deux tirets cadratins ou demi-cadratins.

Une phrase ne compte qu’une fois si elle contient plusieurs incises. Un tiret isolé, notamment le tiret initial d’un dialogue, ne suffit pas. Les catégories techniques spaCy correspondantes sont `appos`, `acl:relcl`, `advcl` et `parataxis`.

<a id="coordination_accumulation_count"></a>
##### Phrases avec accumulation coordonnée (coordination_accumulation_count)
Nombre de phrases comportant plus de deux coordinations reconnues par spaCy (`dep_ == "cc"`). Les virgules seules ne sont pas comptées.



<a id="punctuation_mark_count"></a>
##### Signes de ponctuation (punctuation_mark_count)
Somme des nombres de [points](#period_count), [virgules](#comma_count), [deux-points](#colon_count), [points-virgules](#semicolons_count), [points d’exclamation](#exclamation_point_count), [points d’interrogation](#question_mark_count), [points de suspension](#suspention_point_count), [tirets](#dash_count), [parenthèses](#parenthesis_count) et [guillemets](#quote_mark_count).

<a id="period_count"></a>
##### Points (period_count)
Nombre de caractères `.`.

<a id="suspention_point_count"></a>
##### Points de suspension (suspention_point_count)
Nombre de caractères `…`. La normalisation transforme auparavant les suites `...` en un caractère unique `…`.

<a id="comma_count"></a>
##### Virgules (comma_count)
Nombre de virgules.

<a id="colon_count"></a>
##### Deux-points (colon_count)
Nombre de deux-points.

<a id="exclamation_point_count"></a>
##### Points d’exclamation (exclamation_point_count)
Nombre de points d’exclamation.

<a id="question_mark_count"></a>
##### Points d’interrogation (question_mark_count)
Nombre total de points d’interrogation dans le document.

<a id="semicolons_count"></a>
##### Points-virgules (semicolons_count)
Nombre de points-virgules.

<a id="dash_count"></a>
##### Tirets (dash_count)
Nombre de tirets demi-cadratins (–) et cadratins (—).

<a id="parenthesis_count"></a>
##### Parenthèses (parenthesis_count)
Nombre de signes ouvrants ou fermants de parenthèse.

<a id="quote_mark_count"></a>
##### Guillemets (quote_mark_count)
Nombre de guillemets français (« ou »), anglais (“ ou ”) ou droits (").



<a id="temporal_connector_count"></a>
##### Connecteurs temporels (temporal_connector_count)
Nombre d’occurrences de connecteurs temporels ou séquentiels définis dans `assets/dictionnaires/temporal-connectors.txt`.

<a id="logical_connector_count"></a>
##### Connecteurs logiques (logical_connector_count)
Nombre d’occurrences de connecteurs logiques ou argumentatifs définis dans `assets/dictionnaires/logical-connectors.txt`.

<a id="emotion_word_count"></a>
##### Marqueurs émotionnels (emotion_word_count)
Nombre d’occurrences dont le lemme, la famille lexicale ou l’expression composée figure dans `assets/dictionnaires/emotions.txt`. Les formes sont ramenées à leur lemme avec Morphalou. Une occurrence reconnue dans plusieurs catégories n’est comptée qu’une fois ici : c’est pourquoi ce total ne peut pas être obtenu en additionnant les huit comptages par émotion. Le calcul ne tient compte ni de la négation ni du contexte.

<a id="emotion_sentence_count"></a>
##### Phrases émotionnelles (emotion_sentence_count)
Nombre de phrases contenant au moins un [marqueur émotionnel](#emotion_word_count). Une phrase n’est comptée qu’une fois, même si elle contient plusieurs occurrences ou plusieurs catégories.

<a id="joy_emotion_count"></a>
##### Joie (joy_emotion_count)
Nombre d’occurrences rattachées à la catégorie « Joie » de `assets/dictionnaires/emotions.txt`. Pour les huit catégories, les mots du document sont ramenés à leur lemme avec Morphalou ; le calcul reconnaît les lemmes, leurs familles lexicales et les expressions composées. Il ne tient compte ni de la négation ni du contexte. Une même occurrence peut appartenir à plusieurs catégories si leurs familles lexicales se recouvrent.

<a id="joy_intensified_emotion_count"></a>
##### Joie intensifiée (joy_intensified_emotion_count)
Nombre d’occurrences de joie intensifiées ou qualifiées. Pour les huit catégories, une occurrence est retenue lorsqu’elle est précédée par un intensificateur tel que « très », « tellement » ou « terriblement », ou lorsque spaCy lui rattache un modificateur adjectival (`amod`) ou adverbial (`advmod`).

<a id="sadness_emotion_count"></a>
##### Tristesse (sadness_emotion_count)
Nombre d’occurrences rattachées à la catégorie « Tristesse ».

<a id="sadness_intensified_emotion_count"></a>
##### Tristesse intensifiée (sadness_intensified_emotion_count)
Nombre d’occurrences de tristesse intensifiées ou qualifiées.

<a id="fear_emotion_count"></a>
##### Peur (fear_emotion_count)
Nombre d’occurrences rattachées à la catégorie « Peur ».

<a id="fear_intensified_emotion_count"></a>
##### Peur intensifiée (fear_intensified_emotion_count)
Nombre d’occurrences de peur intensifiées ou qualifiées.

<a id="anger_emotion_count"></a>
##### Colère (anger_emotion_count)
Nombre d’occurrences rattachées à la catégorie « Colère ».

<a id="anger_intensified_emotion_count"></a>
##### Colère intensifiée (anger_intensified_emotion_count)
Nombre d’occurrences de colère intensifiées ou qualifiées.

<a id="surprise_emotion_count"></a>
##### Surprise (surprise_emotion_count)
Nombre d’occurrences rattachées à la catégorie « Surprise ».

<a id="surprise_intensified_emotion_count"></a>
##### Surprise intensifiée (surprise_intensified_emotion_count)
Nombre d’occurrences de surprise intensifiées ou qualifiées.

<a id="disgust_emotion_count"></a>
##### Dégoût (disgust_emotion_count)
Nombre d’occurrences rattachées à la catégorie « Dégoût ».

<a id="disgust_intensified_emotion_count"></a>
##### Dégoût intensifié (disgust_intensified_emotion_count)
Nombre d’occurrences de dégoût intensifiées ou qualifiées.

<a id="contempt_emotion_count"></a>
##### Mépris (contempt_emotion_count)
Nombre d’occurrences rattachées à la catégorie « Mépris ».

<a id="contempt_intensified_emotion_count"></a>
##### Mépris intensifié (contempt_intensified_emotion_count)
Nombre d’occurrences de mépris intensifiées ou qualifiées.

<a id="somatic_emotion_count"></a>
##### Manifestations somatiques (somatic_emotion_count)
Nombre d’occurrences rattachées à la catégorie « Manifestations somatiques ».

<a id="somatic_intensified_emotion_count"></a>
##### Manifestations somatiques intensifiées (somatic_intensified_emotion_count)
Nombre de manifestations somatiques intensifiées ou qualifiées.
<!-- STATS:END -->
