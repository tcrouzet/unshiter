# Dispersion #42

Indique à quel point les valeurs diffèrent dans le corpus. Le calcul commence par écarter les valeurs aberrantes selon la règle de Tukey : toute valeur située à plus de 1,5 fois l’intervalle interquartile sous le premier quartile ou au-dessus du troisième quartile est ignorée. Elle reste affichée dans le tableau, mais ne gonfle pas σ. L’écart-type des valeurs restantes est ensuite divisé par leur moyenne et affiché en pourcentage. Un σ faible signale une mesure non significative.

# **Densité de ponctuations** / Sparsité de ponctuations #1 #tab1_1

Pourcentage de signes de ponctuation par mots sur tout le document. Un style très ponctué est plus haché, plus mitraillé ; un style moins ponctué implique un flot continu.

# **Complexité de ponctuation** / Simplicité de ponctuation #2 #tab1_2

Répartition des signes de ponctuation en dix familles : point, virgule, point-virgule, deux-points, interrogation, exclamation, tiret, parenthèses, guillemets et points de suspension. Le calcul utilise l’entropie de cette répartition, divisée par `log₂(10)` puis ramenée entre 0 et 100 %. Le dénominateur reste donc celui de la palette complète : un texte qui emploie trois familles équilibrées n’atteint pas 100 %, car il n’utilise pas tout l’arsenal disponible. Une faible entropie indique l'usage de peu de ponctuation différente, par exemple seulement des points et virgules, alors qu'une grande entropie implique un usage équilibré de nombreuses familles.

# **Diversité syntaxique** / Régularité syntaxique #3 #tab1_3

Chaque phrase est d’abord transformée en propositions simplifiées, par exemple `SUJET VERBE COMPLÉMENT` ou `PROPOSITION_SUBORDONNÉE`. Les déterminants et prépositions n'ont pas de rôles. Les virgules et les points sont conservés dans les propositions ordinaires. Les répétitions internes sont comptées : une phrase peut ainsi devenir `SUJET VERBE COMPLÉMENT + 5 PROPOSITIONS_SUBORDONNÉES`.

Deux phrases sont comparées en combinant deux distances : 75 % pour la différence entre les proportions de leurs constructions et 25 % pour la différence entre leurs nombres d’occurrences. Cette distance est ensuite pondérée par la quantité d’information disponible : le poids augmente avec le nombre cumulé de propositions et atteint son maximum à douze. Deux phrases très courtes ne peuvent donc pas créer seules une opposition maximale. À l’inverse, cinq subordonnées identiques apportent moins de diversité que cinq constructions différentes. La valeur finale est la moyenne des distances entre toutes les paires de phrases, de 0 à 100 %.

# **Alternance structurelle** / Régularité structurelle #4 #tab1_4

Compare chaque structure de phrase à la suivante dans l’ordre du texte. La distance d’édition compte les rôles qu’il faudrait ajouter, supprimer ou remplacer pour passer d’un patron à l’autre, puis divise ce nombre par la longueur du patron le plus long. Le résultat final est la moyenne de ces distances. 0 % signifie que les mêmes patrons se succèdent ; une valeur élevée indique des changements structurels fréquents.

# **Diversité des débuts de phrase** / Régularité des débuts de phrase #5 #tab1_6

Pour chaque phrase, le premier mot est relevé après tokenisation. Le calcul examine des fenêtres glissantes de vingt phrases et mesure, dans chacune, le nombre de premiers mots différents divisé par vingt. Le rapport affiche la moyenne de ces fenêtres. Si le texte compte moins de vingt phrases, le calcul porte sur toutes ses phrases. 100 % signifie qu’aucun début ne se répète dans la fenêtre considérée.

# **Diversité locale de longueur de phrase** / Uniformité locale de longueur de phrase #6 #tab1_7

Pour chaque paire de phrases consécutives, le calcul prend la différence absolue de longueur en caractères. La moyenne de ces différences est divisée par la longueur moyenne des phrases. Une valeur de 0 indique des phrases successives de même longueur. La division par la moyenne permet de comparer des textes composés de phrases globalement courtes ou longues. Cette mesure est traditionnellement nommée burstiness (par rafales, par à-coups).

# Style nominal / **Style verbal** #7 #tab1_8

Nombre de noms reconnu par [Morphalou](https://www.ortolang.fr/market/lexicons/morphalou/v3.1) divisé par le nombre de verbes reconnu par Morphalou. Une valeur de 2 signifie que le texte contient deux noms pour un verbe.

Un ratio élevé traduit un style nominal : le texte s'appuie sur des substantifs plutôt que sur des actions, souvent au prix d'une syntaxe plus statique — descriptions, énumérations, écriture administrative ou théorique, phrases qui exposent plutôt qu'elles ne racontent. À l'inverse, un ratio bas traduit un style verbal : le texte progresse par l'action, les procès, les enchaînements d'événements — un rythme plus narratif et dynamique, où les choses se passent plutôt qu'elles ne sont.

# Redondance lexicale / **Renouvellement lexical** #8 #tab1_9

Mesures les répétitions sur une fenêtre de {windows}. Pour chaque mot, cherche le même lemme parmi les 300 mots précédents. Les flexions sont donc regroupées : `marche`, `marches` et `marchaient` peuvent renvoyer au même lemme. Le pourcentage est le nombre de mots ayant un antécédent divisé par le nombre total de mots analysés. Les mots-outils et les graphies de moins de deux caractères ne peuvent pas être signalés, mais le dénominateur reste l’ensemble des mots retenus. La lemmatisation contextuelle vient de spaCy, avec Morphalou comme repli.

# Redondance lexicale locale / Renouvellement lexical local #9

Dans une fenêtre de {windows}, le programme parcourt les mots dans l’ordre. Pour chaque mot, il cherche une occurrence précédente située au plus à 300 mots de distance. Si une telle occurrence existe, une seule pression est retenue selon la correspondance la plus forte : 1 pour une graphie identique ; sinon 0,25 pour le même lemme ; sinon 0,25 pour la même famille morphologique. Les pressions ne sont donc pas cumulatives : un même lemme n’ajoute pas aussi une pression de famille. Les mots-outils et noms propres sont écartés. La pression totale est divisée par le nombre de mots puis plafonnée à 100 %. Une diversité stylistique élevée signifie donc une faible pression de ces répétitions locales.

# Répétition de familles de mots / Diversité des familles de mots #10

Dans une fenêtre de {windows}, même calcul local que les redondances lexicales, mais deux mots sont aussi rapprochés lorsqu’ils appartiennent à une même famille morphologique dans [Démonette](https://demonette.fr/demonext/vues/front_page.php), par exemple `écrire`, `écrivain` et `écriture`. Pour chaque mot, une ou plusieurs correspondances dans les 300 mots précédents comptent comme une seule répétition.

# Répétition sonore / Diversité sonore #11

Pour chaque mot dans une fenêtre de {windows}, le programme cherche dans les 300 mots précédents une prononciation partageant une suite continue d’au moins trois phonèmes. Cette suite doit couvrir au moins 60 % de la prononciation la plus courte. Le pourcentage indique la part des mots pour lesquels un tel écho a été trouvé. Cette approximation phonétique ne remplace pas une lecture à voix haute.

# Redondance lexicale brute / Renouvellement lexical brut #12

Même calcul que les répétitions lexicales, mais en conservant les mots-outils. La mesure inclut donc les répétitions grammaticales ordinaires du français et sera naturellement beaucoup plus élevée que la version filtrée.

# Densité grammaticale / **Densité lexicale** #13

Part des mots classés comme déterminants, pronoms, prépositions, conjonctions ou interjections. Les adverbes ne sont pas inclus. La liste éditable se trouve dans `assets/function-words.txt` et complète les catégories de Morphalou. Cette mesure décrit la place du matériel grammatical dans le texte ; elle ne constitue pas à elle seule un jugement de qualité.

Une valeur élevée signifie que le texte s'appuie beaucoup sur le matériel grammatical (déterminants, pronoms, prépositions, conjonctions, interjections) — souvent des phrases courtes, un style oral ou fluide. Une valeur basse signifie que le texte est porté par les mots pleins (noms, verbes, adjectifs, adverbes) — style plus dense, informatif ou nominal.

# Redondance globale des trigrammes / Renouvellement global des trigrammes #14

Un trigramme est une suite de trois lemmes consécutifs. Dans une fenêtre de {windows}, chaque mot est d’abord remplacé par son lemme contextuel : `marche`, `marches` et `marchent` employés comme verbes deviennent ainsi `marcher`, tandis que le nom dans `la marche` reste `marche`. spaCy désambiguïse la catégorie grâce à la phrase ; Morphalou sert de repli lorsque cette analyse contextuelle est indisponible. Le programme compte les trigrammes distincts présents plus d’une fois, puis divise ce nombre par le nombre total de trigrammes distincts. Il s’agit donc d’une proportion de types répétés, et non de toutes les occurrences répétées.

# Redondance locale des trigrammes / Renouvellement local des trigrammes #15

Même proportion de trigrammes de lemmes distincts répétés, calculée dans des fenêtres glissantes de 300 mots espacées de 50 mots, puis moyennée. Cette version privilégie les formulations qui reviennent à proximité dans une fenêtre de {windows}, .

# Densité des noms / Sparcité des noms #16

Nombre de mots classés comme noms par Morphalou, divisé par le nombre total de mots auxquels Morphalou attribue une catégorie grammaticale. Les quatre lignes noms, verbes, adjectifs et adverbes ne totalisent pas nécessairement 100 %, car le dénominateur comprend aussi d’autres catégories.

# Densité des Verbes / Sparcité des verbes #17

Nombre de mots classés comme verbes par Morphalou, divisé par le nombre total de mots auxquels Morphalou attribue une catégorie grammaticale.

# Densité des adjectifs / Sparcité des adjectifs #18

Nombre de mots classés comme adjectifs par Morphalou, divisé par le nombre total de mots auxquels Morphalou attribue une catégorie grammaticale.

# Densité des adverbes / Sparcité des adverbes #19

Nombre de mots classés comme adverbes par Morphalou, divisé par le nombre total de mots auxquels Morphalou attribue une catégorie grammaticale.

# **Compressibilité gzip** / Incompressibilité gzip #21

Le texte UTF-8 est compressé avec gzip. La taille compressée est divisée par la taille originale et affichée en pourcentage. Une valeur basse signifie que les octets du texte sont plus prévisibles et se compressent mieux. Pour comparer les documents, le programme utilise des blocs non chevauchants ayant exactement {window}.

# **Densité de relatives et subordonnées** / Sparcité de relatives et subordonnées #22

spaCy compte les dépendances de relative (`acl:relcl`) et les autres dépendances subordonnées configurées (`acl`, `advcl`, `ccomp`, `csubj`, `xcomp`). Leur somme est divisée par le nombre de phrases. La valeur peut dépasser 100 % : une phrase peut contenir plusieurs subordonnées. Ce résultat dépend de l’analyse du modèle spaCy.

# Densité de phrases nominales / Sparcité de phrases nominales #23

Part des phrases dans lesquelles spaCy ne trouve aucun verbe conjugué. Les infinitifs et participes isolés ne suffisent pas à rendre la phrase verbale. La mesure repère notamment des ruptures comme « Un cauchemar. Encore un. », mais dépend de la qualité de l’analyse syntaxique.

# **Densité de voix active** / Densité de voix passive #24

Pourcentage des phrases du document contenant une construction verbale active et aucune construction passive. Le passif est reconnu par une dépendance `aux:pass`, un sujet `nsubj:pass` ou la marque morphologique `Voice=Pass`. La présence de l’auxiliaire « être » ne suffit pas : dans « il était allé », « était » construit un temps composé actif. 100 % signifie que toutes les phrases sont verbales et actives. Cette mesure est calculée sur le document entier, sans fenêtre.

# Densité de métaphores / Sparcité de métaphores #25

Pourcentage des phrases du document contenant au moins une comparaison détectée. Le programme reconnaît les « comme » comparatifs ainsi que les locutions inscrites dans `assets/comparison-markers.txt`. « Il courait comme un chien enragé » et « Il courait comme Charlot courait » sont comptés ; « Comme il pleuvait, il restait chez lui » ne l’est pas. 100 % signifie que chaque phrase contient au moins une comparaison. Cette mesure est calculée sur le document entier, sans fenêtre. Elle repère une forme comparative, sans pouvoir garantir que l’image soit sémantiquement une métaphore.

# **Complexité syntaxique** / Minimalisme syntaxique #26 #tab1_5

Mesure la complexité hiérarchique des phrases reconnue par spaCy. Plus des groupes et propositions sont emboîtés les uns dans les autres, plus les mots les plus éloignés nécessitent de relations pour rejoindre le verbe principal, et plus la profondeur augmente.

L'idée : une phrase simple (« Le chat dort ») a une profondeur faible — un seul niveau entre le mot et le verbe. Une phrase à subordonnées empilées (« Le chat que le voisin, qui venait d'emménager, avait recueilli dormait ») a une profondeur élevée — plusieurs relations à traverser pour remonter jusqu'au verbe principal.

# Minimalisme flexionnel / Variation flexionnelle #27

Dans chaque fenêtre mobile de 300 mots, la diversité des formes graphiques est divisée par la diversité des lemmes. Un ratio proche de 1 signifie que chaque lemme n'apparaît quasiment que sous une seule forme (peu de variation flexionnelle : toujours "marche", jamais "marchait" ou "marchions"). Un ratio élevé signifie qu'un même lemme revient sous de nombreuses formes différentes (le texte varie les temps, les nombres, les genres pour une même racine).

# **Taux d'hapax** / Taux de récurrence #28

Nombre de lemmes lexicaux Morphalou apparaissant exactement une fois, divisé par le nombre de lemmes lexicaux distincts.

Un taux élevé signifie que le texte introduit beaucoup de mots qu'il n'utilise ensuite plus jamais (vocabulaire riche et non répété, parfois signe d'un style très varié ou au contraire de rareté statistique) ; un taux bas signifie que le vocabulaire lexical est concentré sur peu de lemmes, réemployés souvent.

# **Diversité de longueurs de phrase** / Uniformité des longueur de phrase  #41

Dans la fenêtre {windows}, écart-type du nombre de mots par phrase. Une valeur élevée indique une alternance plus forte entre phrases courtes et longues. La diversité des structures intègre déjà une partie de cette information en accordant progressivement davantage de poids aux phrases contenant plusieurs propositions. 

# Couverture stylistique #29

Surface sur le graphique radar en fonction des valeurs affichées. C'est une signature stylistique et non un critère de qualité.

Pour rendre les axes comparables, le radar établit ses repères une seule fois sur tout le corpus, jamais sur la sélection affichée. La valeur est d'abord située linéairement entre le minimum et le maximum du corpus, puis transformée par une courbe logarithmique `log(1 + 4x) / log(5)`. Cette courbe continue étale les valeurs basses et ralentit progressivement l'approche de 100 %, sans supprimer ni saturer brutalement aucune œuvre. La transformation s'applique aux coordonnées du radar et au calcul de sa surface, sans modifier les valeurs brutes des tableaux.

Ce tassemment modère l'influence des choix stylistiques extrêmes, comme les phrases très longues qui mécaniquement tirent beaucoup d'indices à la hausse.

# Mots #30

Nombre total de mots relevés dans le document analysé.

# Phrases #31

Nombre total de phrases relevées dans le document analysé.

# Paragraphes #32

Nombre total de paragraphes relevés dans le document analysé.

# Longueur moyenne des mots (caractères) #33

Nombre moyen de caractères par mot dans le document analysé.

# Longueur moyenne des phrases (caractères) #34

Nombre moyen de caractères par phrase dans le document analysé.

# Longueur médiane des phrases (caractères) #36

Longueur en caractères qui partage les phrases en deux groupes de même effectif.

# Longueur P10 des phrases (caractères) #37

Longueur en caractères sous laquelle se trouvent 10 % des phrases.

# Longueur P90 des phrases #38

Longueur en caractères sous laquelle se trouvent 90 % des phrases.

# Écart-type des paragraphes #39

Écart-type du nombre de mots par paragraphe. Il mesure la dispersion des longueurs de paragraphes autour de leur moyenne.

# Caractères #40

Nombre total de caractères du document analysé, espaces et retours à la ligne compris.

# Singularité #43

Distance de Burrows calculée sur trente-deux mesures stylistiques. Chaque mesure est d’abord centrée et réduite sur l’ensemble du corpus ; la distance entre deux œuvres est la moyenne des écarts absolus entre leurs z-scores. Le graphique affiche, pour chaque œuvre ou auteur sélectionné, la distance à son voisin le plus proche. Une valeur faible indique une proximité statistique, pas une identité d’auteur ni une preuve d’influence. Cette vue répond à la question « ce texte est-il isolé ou proche d’un autre ? » ; elle ne suffit pas à attribuer une ressemblance à un auteur.

# Carte stylistique MDS #44

Projection en deux dimensions des distances de Burrows calculées sur trente-deux mesures. Les œuvres proches dans la carte sont proches dans l’espace multidimensionnel ; les axes de la projection n’ont pas de signification littéraire propre. Le stress indique la part de déformation introduite par la réduction à deux dimensions : plus il est faible, plus la carte respecte les distances originales.

# Voisinage stylistique #45

Pour l’œuvre choisie, les œuvres les plus proches sont classées par percentile décroissant. L’axe affiche le percentile de proximité dans toutes les distances du corpus : 90 % signifie que l’œuvre est plus proche que 90 % des paires comparées. Le titre du tableau donne directement le nombre de voisins par auteur. Les couleurs identifient les auteurs ; l’auteur de référence est affiché en couleur pleine afin que le nombre de voisins du même auteur soit immédiatement lisible. Une œuvre peut être épinglée pour apparaître en ligne supplémentaire, avec son rang réel dans le classement. Ces repères sont descriptifs et ne constituent pas une preuve d’attribution.

# **Densité de participes présents** / Sparcité de participes présents #64

Part des formes verbales identifiées comme participes présents (`VerbForm=Part`, `Tense=Pres`) parmi les mots analysés. Elles sont séparées des verbes conjugués.

# **Densité de participes passés** / Sparcité de participes passés #65

Part des formes verbales identifiées comme participes passés (`VerbForm=Part`, `Tense=Past`) parmi les mots analysés. Un participe employé comme adjectif est compté dans les adjectifs, pas ici.
