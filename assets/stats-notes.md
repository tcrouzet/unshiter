# Delta

Δ est la différence entre Lettre 1, texte IA de référence, et la moyenne des deux textes humains confirmés, Réponse et Roman. Cette différence est divisée par la valeur maximale possible de la mesure et exprimée en pourcentage. Lorsqu’aucun maximum théorique n’est défini, le maximum observé sert de référence. Lettre 2, texte hybride réécrit, est exclue. Une valeur proche de 0 % indique une mesure presque plate. Δ n’est pas affiché pour les simples données techniques.

# IA

Plus cet indice est élévé, plus le texte serait suceptible d'être généré par une iA. Combine les mesures les plus sinificaves ci-dessous.

Poids actuels : répétition des structures 20 %, faible diversité des structures 15 %, faible diversité syntaxique 10 %, faible densité de ponctuation 15 %, faible diversité de ponctuation 15 %, faible variété des débuts de phrase 15 %, faible taux de phrases nominales 5 %, relatives et subordonnées 5 %. Ces poids sont ajustés sur le petit corpus présent et ne constituent pas une probabilité.

# Diversité syntaxique

Le calcul combine six signaux continus : amplitude relative, burstiness, répétitions lexicales, répétition des structures, diversité des structures et rythme des structures. Plus la valeur est élevée, plus le texte est diversifié.

# Amplitude (caractères)

L’amplitude mesure la diversité globale des longueurs de phrases, en nombre de caractères.

# Burstiness

La burstiness est l’écart moyen en caractères entre des phrases consécutives, divisé par la longueur moyenne des phrases. Plus la valeur est élevée, plus le rythme présente de diversité.

# Répétitions stylistiques

Cet indice mesure la pression des chaînes répétitives dans un empan de 300 mots. Chaque paire de graphies identiques compte pleinement ; deux flexions d’un même lemme ou deux mots d’une même famille comptent pour un quart. Les mots-outils et les noms propres sont écartés. Une série concentrée pèse ainsi davantage que plusieurs répétitions isolées. Cet indice s’inspire du fonctionnement documenté d’Antidote sans prétendre reproduire son filtre propriétaire.

# Répétitions lexicales

Le taux de répétition est la part des mots qui reprennent un des 300 lemmes précédents. Par exemple marche, marches et marchent sont regroupés sous marcher (la sonnorité importe). Le taux filtré ne compte pas les déterminants, conjonctions, prépositions, pronoms et interjections dans les répétitions. Les calculs comparatifs restent effectués sur des fenêtres de la taille du texte le plus court.

# Répétitions familiales

Les répétitions familiales regroupent les lemmes appartenant à une même famille morphologique dans Démonette, par exemple écrire, écrivain et écriture.

# Répétitions sonores

Les répétitions sonores rapprochent les mots qui partagent une séquence phonétique significative dans les 300 mots précédents. Elles mesurent les échos perceptibles à l’oreille, même lorsque les lemmes diffèrent.

# Phrases nominales

Part des phrases qui ne contiennent aucun verbe conjugué.

# Mots-outils

Déterminants, pronoms, prépositions, conjonctions, interjections. Leur pourcentage indique la place occupée par ces mots dans le texte. Il renseigne sur la densité syntaxique.

# Répétition des structures

Décompte les structures syntaxiques et repère celles qui se répettent.

# Diversité des structures

La diversité des structures est le nombre de patrons syntaxiques différents divisé par le nombre de structures admissibles. 100 % signifie que chaque structure n’apparaît qu’une fois ; une valeur faible indique qu’un petit nombre de patrons domine le texte (style monotomne).

# Rythme des structures

Le rythme des structures mesure la différence moyenne entre deux patrons syntaxiques consécutifs. Le calcul compare les ajouts, suppressions et remplacements de rôles syntaxiques, puis rapporte cette différence à la longueur du patron le plus long. 0 % signifie que les mêmes structures se succèdent ; une valeur élevée indique de fortes variations structurelles d’une phrase à la suivante.

# Compression gzip

Taille du texte compressé divisée par sa taille originale. Une valeur faible indique un texte plus répétitif et prévisible, donc plus facile à compresser.

# Relatives et subordonnées

Nombre de propositions relatives et subordonnées rapporté au nombre de phrases. La valeur peut dépasser 100 % parce qu’une même phrase peut contenir à la fois une relative et une ou plusieurs autres subordonnées. Pour le calcul de Δ, cette mesure combinée est normalisée sur un maximum de 200 %.

# Ponctuation (signes/300 mots)

Nombre total de signes de ponctuation pour 300 mots, sur la même échelle que les fenêtres de comparaison. Une valeur faible contribue actuellement à l’indice IA.

# Diversité de ponctuation

Diversité des types de signes de ponctuation employés. Une valeur faible contribue actuellement à l’indice IA.

# Variété des débuts de phrase

Diversité des premiers mots des phrases, moyennée sur les fenêtres comparables. Une valeur faible contribue actuellement à l’indice IA.

# Profondeur syntaxique

La profondeur syntaxique est la moyenne, pour chaque phrase, du plus grand nombre de liens entre un mot et la racine de son arbre de dépendances. Elle est calculée par le modèle français `fr_core_news_sm` de spaCy. Une valeur élevée indique des phrases dont les dépendances grammaticales sont plus imbriquées.

# Variation des phrases (mots)

Écart-type de la longueur des phrases en nombre de mots. Pour Δ, l’écart IA–humains est rapporté à la longueur moyenne des phrases en mots.

# Noms

Part des noms parmi les mots classés comme noms, verbes, adjectifs ou adverbes.

# Verbes

Part des verbes parmi les mots classés comme noms, verbes, adjectifs ou adverbes.

# Adjectifs

Part des adjectifs parmi les mots classés comme noms, verbes, adjectifs ou adverbes.

# Adverbes

Part des adverbes parmi les mots classés comme noms, verbes, adjectifs ou adverbes.

# Diversité des formes

Part moyenne de formes graphiques différentes dans les fenêtres comparables.

# Diversité lemmatisée

Part moyenne de lemmes différents dans les fenêtres comparables.

# Mots employés une seule fois

Part des formes qui n’apparaissent qu’une fois dans la fenêtre analysée.

# Répétition globale des trigrammes

Part des suites de trois mots qui apparaissent plusieurs fois dans le texte analysé.

# Répétition locale des trigrammes

Part moyenne des suites de trois mots répétées dans des fenêtres locales.

# Taux de répétition non filtré

Part des mots qui reprennent un lemme précédent, mots-outils compris.

# Lisibilité Flesch

Indice de lisibilité adapté au français à partir de la longueur des phrases et du nombre de syllabes. Une valeur élevée indique généralement un texte plus facile à lire.

# Mots

Nombre total de mots du document complet.

# Phrases

Nombre total de phrases du document complet.

# Paragraphes

Nombre total de paragraphes du document complet ; un ou plusieurs sauts de ligne vides séparent deux paragraphes.

# Longueur moyenne des mots (caractères)

Nombre moyen de caractères par mot.

# Longueur moyenne des phrases (caractères)

Nombre moyen de caractères par phrase, espaces compris.

# Longueur moyenne des phrases (mots)

Nombre moyen de mots par phrase.

# Longueur médiane des phrases (caractères)

Longueur en caractères qui partage les phrases en deux groupes de même effectif.

# Longueur P10 des phrases (caractères)

Longueur en caractères sous laquelle se trouvent 10 % des phrases.

# Longueur P90 des phrases (caractères)

Longueur en caractères sous laquelle se trouvent 90 % des phrases.

# Écart-type des phrases (caractères)

Dispersion brute de la longueur des phrases autour de leur moyenne, en caractères.

# Écart-type des paragraphes (mots)

Dispersion brute de la longueur des paragraphes autour de leur moyenne, en mots.

# Fenêtres de répétition analysées

Nombre de fenêtres comparables utilisées pour moyenner les mesures du document.

# Longueur moyenne des paragraphes

Nombre moyen de mots par paragraphe.
