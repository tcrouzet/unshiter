# Δ

Différence entre texte IA de référence et la moyenne des textes humains confirmés. Cette différence est divisée par la valeur maximale possible de la mesure et exprimée en pourcentage. Lorsqu’aucun maximum théorique n’est défini, le maximum observé sert de référence. Une valeur proche de 0 % indique des mesures peu discriminante. Δ n’est pas affiché pour les données techniques.

# IA

Plus cet indice est élevé, plus le texte serait susceptible d'être généré par une IA. Poids actuels : répétition des structures 25 %, faible diversité des structures 20 %, faible densité de ponctuation 15 %, faible diversité de ponctuation 15 %, faible variété des débuts de phrase 15 %, faible taux de phrases nominales 5 %, relatives et subordonnées 5 %. Ces poids sont ajustés sur le petit corpus présent et ne constituent pas une probabilité.

# Répétition des structures

Décompte les structures syntaxiques et repère celles qui se répètent.

# Diversité des structures

Nombre de patrons syntaxiques différents divisé par le nombre de phrases analysées. Une valeur faible indique qu’un petit nombre de patrons domine le texte (style monotone).

# Relatives et subordonnées

Nombre de propositions relatives et subordonnées rapporté au nombre de phrases. La valeur peut dépasser 100 % parce qu’une même phrase peut contenir à la fois des relatives et une ou des subordonnées. Les IA ont tendance à abuser des relatives et subordonnées (mais un prompt habile peut les limiter).

# Ponctuation (signes/300 mots)

Nombre total de signes de ponctuation pour 300 mots. Les IA ont tendance à utiliser moins de ponctuation que les humains.

# Diversité de ponctuation

Diversité des ponctuations employées. Les IA sont moins éclectiques que les humains par défaut.

# Phrases nominales

Les IA utilisent peu de phrases nominales par défaut.

# Variété des débuts de phrase

Diversité des premiers mots des phrases. Les IA ont tendance à écrire des phrases qui se ressemblent.

# Amplitude (caractères)

L’amplitude mesure la diversité globale des longueurs de phrases, en nombre de caractères.

# Variation des phrases (mots)

Écart-type de la longueur des phrases en nombre de mots.

# Burstiness

La burstiness est l’écart moyen en caractères entre des phrases consécutives, divisé par la longueur moyenne des phrases. Plus la valeur est élevée, plus le rythme présente de diversité.

# Répétitions stylistiques

Cet indice mesure la pression des chaînes répétitives dans un empan de 300 mots. Chaque paire de graphies identiques compte pleinement ; deux flexions d’un même lemme ou deux mots d’une même famille comptent pour un quart. Les mots-outils et les noms propres sont écartés. Une série concentrée pèse ainsi davantage que plusieurs répétitions isolées. Cet indice s’inspire du fonctionnement documenté d’Antidote sans prétendre reproduire son filtre propriétaire.

# Répétitions lexicales

Part des mots qui reprennent un des 300 lemmes précédents. Par exemple marche, marches et marchent sont regroupés sous marcher. Le taux filtré ne compte pas les déterminants, conjonctions, prépositions, pronoms et interjections dans les répétitions. Les calculs comparatifs restent effectués sur des fenêtres de la taille du texte le plus court.

# Répétitions familiales

Regroupent les lemmes appartenant à une même famille morphologique dans Démonette, par exemple écrire, écrivain et écriture.

# Répétitions sonores

Les répétitions sonores rapprochent les mots qui partagent une séquence phonétique significative dans les 300 mots précédents. Elles mesurent les échos perceptibles à l’oreille, même lorsque les lemmes diffèrent.

# Mots-outils

Déterminants, pronoms, prépositions, conjonctions, interjections. Leur pourcentage indique la place occupée par ces mots dans le texte. Il renseigne sur la densité syntaxique.

# Noms

Part des noms parmi les mots classés comme noms, verbes, adjectifs ou adverbes.

# Verbes

Part des verbes parmi les mots classés comme noms, verbes, adjectifs ou adverbes.

# Adjectifs

Part des adjectifs parmi les mots classés comme noms, verbes, adjectifs ou adverbes.

# Adverbes

Part des adverbes parmi les mots classés comme noms, verbes, adjectifs ou adverbes.

# Rythme des structures

Le rythme des structures mesure la différence moyenne entre deux patrons syntaxiques consécutifs. Le calcul compare les ajouts, suppressions et remplacements de rôles syntaxiques, puis rapporte cette différence à la longueur du patron le plus long : 0 % signifie que les mêmes structures se succèdent ; une valeur élevée indique de fortes variations structurelles d’une phrase à la suivante.

# Compression gzip

Taille du texte compressé divisée par sa taille originale. Une valeur faible indique un texte plus répétitif et prévisible, donc plus facile à compresser.

# Profondeur syntaxique

La profondeur syntaxique est la moyenne, pour chaque phrase, du plus grand nombre de liens entre un mot et la racine de son arbre de dépendances. Elle est calculée par le modèle français `fr_core_news_sm` de spaCy. Une valeur élevée indique des phrases dont les dépendances grammaticales sont plus imbriquées.

# Diversité des formes

Part moyenne de formes graphiques différentes dans les fenêtres analysées.

# Diversité lemmatisée

Part moyenne de lemmes différents dans les fenêtres analysées.

# Mots employés une seule fois

Part des formes qui n’apparaissent qu’une fois dans la fenêtre analysée.

# Répétition globale des trigrammes

Part des suites de trois mots qui apparaissent plusieurs fois dans le texte analysé.

# Répétition locale des trigrammes

Part moyenne des suites de trois mots répétées dans des fenêtres locales.

# Taux de répétition non filtré

Part des mots qui reprennent un lemme précédent, mots-outils compris.
