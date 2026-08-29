# Dispersion (note_dispersion)
Indique à quel point les valeurs diffèrent dans le corpus. Chaque valeur est d’abord divisée par le maximum observé pour cette mesure dans le corpus complet, puis ramenée sur une échelle de 0 à 100. σ est l’écart-type de ces valeurs normalisées : `std([v / max_corpus × 100])`. Il est donc indépendant de l’unité native et ne pénalise pas les marqueurs rares. Une mesure est considérée comme significativement dispersée lorsque σ est supérieur ou égal à 5 sur cette échelle normalisée.

# **Densité de ponctuations** / Sparsité de ponctuations (punctuation_per_300_words)
Pourcentage de signes de ponctuation par mots sur tout le document. Un style très ponctué est plus haché, plus mitraillé ; un style moins ponctué implique un flot continu.

# **Complexité de ponctuation** / Simplicité de ponctuation (punctuation_diversity)
Répartition des signes de ponctuation en dix familles : point, virgule, point-virgule, deux-points, interrogation, exclamation, tiret, parenthèses, guillemets et points de suspension. Le calcul utilise l’entropie de cette répartition, divisée par `log₂(10)` puis ramenée entre 0 et 100 %. Le dénominateur reste donc celui de la palette complète : un texte qui emploie trois familles équilibrées n’atteint pas 100 %, car il n’utilise pas tout l’arsenal disponible. Une faible entropie indique l'usage de peu de ponctuation différente, par exemple seulement des points et virgules, alors qu'une grande entropie implique un usage équilibré de nombreuses familles.

# **Diversité syntaxique** / Régularité syntaxique (structural_diversity)
Chaque phrase est d’abord transformée en propositions simplifiées, par exemple `SUJET VERBE COMPLÉMENT` ou `PROPOSITION_SUBORDONNÉE`. Les déterminants et prépositions n'ont pas de rôles. Les virgules et les points sont conservés dans les propositions ordinaires. Les répétitions internes sont comptées : une phrase peut ainsi devenir `SUJET VERBE COMPLÉMENT + 5 PROPOSITIONS_SUBORDONNÉES`.

Deux phrases sont comparées en combinant deux distances : 75 % pour la différence entre les proportions de leurs constructions et 25 % pour la différence entre leurs nombres d’occurrences. Cette distance est ensuite pondérée par la quantité d’information disponible : le poids augmente avec le nombre cumulé de propositions et atteint son maximum à douze. Deux phrases très courtes ne peuvent donc pas créer seules une opposition maximale. À l’inverse, cinq subordonnées identiques apportent moins de diversité que cinq constructions différentes. La valeur finale est la moyenne des distances entre toutes les paires de phrases, de 0 à 100 %.

# **Alternance structurelle** / Régularité structurelle (structural_rhythm)
Compare chaque structure de phrase à la suivante dans l’ordre du texte. La distance d’édition compte les rôles qu’il faudrait ajouter, supprimer ou remplacer pour passer d’un patron à l’autre, puis divise ce nombre par la longueur du patron le plus long. Le résultat final est la moyenne de ces distances. 0 % signifie que les mêmes patrons se succèdent ; une valeur élevée indique des changements structurels fréquents.

# **Diversité des débuts de phrase** / Régularité des débuts de phrase (sentence_start_diversity)
Pour chaque phrase, le premier mot est relevé après tokenisation. Le calcul examine des fenêtres glissantes de vingt phrases et mesure, dans chacune, le nombre de premiers mots différents divisé par vingt. Le rapport affiche la moyenne de ces fenêtres. Si le texte compte moins de vingt phrases, le calcul porte sur toutes ses phrases. 100 % signifie qu’aucun début ne se répète dans la fenêtre considérée.

# **Diversité locale de longueur de phrase** / Uniformité locale de longueur de phrase (burstiness)
Pour chaque paire de phrases consécutives, le calcul prend la différence absolue de longueur en caractères. La moyenne de ces différences est divisée par la longueur moyenne des phrases. Une valeur de 0 indique des phrases successives de même longueur. La division par la moyenne permet de comparer des textes composés de phrases globalement courtes ou longues. Cette mesure est traditionnellement nommée burstiness (par rafales, par à-coups).

# Style nominal / **Style verbal** (noun_verb_ratio)
Nombre de noms reconnu par [Morphalou](https://www.ortolang.fr/market/lexicons/morphalou/v3.1) divisé par le nombre de verbes reconnu par Morphalou. Une valeur de 2 signifie que le texte contient deux noms pour un verbe.

Un ratio élevé traduit un style nominal : le texte s'appuie sur des substantifs plutôt que sur des actions, souvent au prix d'une syntaxe plus statique — descriptions, énumérations, écriture administrative ou théorique, phrases qui exposent plutôt qu'elles ne racontent. À l'inverse, un ratio bas traduit un style verbal : le texte progresse par l'action, les procès, les enchaînements d'événements — un rythme plus narratif et dynamique, où les choses se passent plutôt qu'elles ne sont.

# Redondance lexicale / **Renouvellement lexical** (filtered_repetition_rate)
Mesures les répétitions sur une fenêtre de {windows}. Pour chaque mot, cherche le même lemme parmi les 300 mots précédents. Les flexions sont donc regroupées : `marche`, `marches` et `marchaient` peuvent renvoyer au même lemme. Le pourcentage est le nombre de mots ayant un antécédent divisé par le nombre total de mots analysés. Les mots-outils et les graphies de moins de deux caractères ne peuvent pas être signalés, mais le dénominateur reste l’ensemble des mots retenus. La lemmatisation contextuelle vient de spaCy, avec Morphalou comme repli.

# Redondance lexicale locale / Renouvellement lexical local (stylistic_repetition_rate)
Dans une fenêtre de {windows}, le programme parcourt les mots dans l’ordre. Pour chaque mot, il cherche une occurrence précédente située au plus à 300 mots de distance. Si une telle occurrence existe, une seule pression est retenue selon la correspondance la plus forte : 1 pour une graphie identique ; sinon 0,25 pour le même lemme ; sinon 0,25 pour la même famille morphologique. Les pressions ne sont donc pas cumulatives : un même lemme n’ajoute pas aussi une pression de famille. Les mots-outils et noms propres sont écartés. La pression totale est divisée par le nombre de mots puis plafonnée à 100 %. Une diversité stylistique élevée signifie donc une faible pression de ces répétitions locales.

# Répétition de familles de mots / Diversité des familles de mots (family_repetition_rate)
Dans une fenêtre de {windows}, même calcul local que les redondances lexicales, mais deux mots sont aussi rapprochés lorsqu’ils appartiennent à une même famille morphologique dans [Démonette](https://demonette.fr/demonext/vues/front_page.php), par exemple `écrire`, `écrivain` et `écriture`. Pour chaque mot, une ou plusieurs correspondances dans les 300 mots précédents comptent comme une seule répétition.

# Répétition sonore / Diversité sonore (phonetic_repetition_rate)
Pour chaque mot dans une fenêtre de {windows}, le programme cherche dans les 300 mots précédents une prononciation partageant une suite continue d’au moins trois phonèmes. Cette suite doit couvrir au moins 60 % de la prononciation la plus courte. Le pourcentage indique la part des mots pour lesquels un tel écho a été trouvé. Cette approximation phonétique ne remplace pas une lecture à voix haute.

# Redondance lexicale brute / Renouvellement lexical brut (absolute_repetition_rate)
Même calcul que les répétitions lexicales, mais en conservant les mots-outils. La mesure inclut donc les répétitions grammaticales ordinaires du français et sera naturellement beaucoup plus élevée que la version filtrée.

# Densité grammaticale / **Densité lexicale** (function_word_ratio)
Part des mots classés comme déterminants, pronoms, prépositions, conjonctions ou interjections. Les adverbes ne sont pas inclus. La liste éditable se trouve dans `assets/dictionnaires/function-words.txt` et complète les catégories de Morphalou. Cette mesure décrit la place du matériel grammatical dans le texte ; elle ne constitue pas à elle seule un jugement de qualité.

Une valeur élevée signifie que le texte s'appuie beaucoup sur le matériel grammatical (déterminants, pronoms, prépositions, conjonctions, interjections) — souvent des phrases courtes, un style oral ou fluide. Une valeur basse signifie que le texte est porté par les mots pleins (noms, verbes, adjectifs, adverbes) — style plus dense, informatif ou nominal.

# Redondance globale des trigrammes / Renouvellement global des trigrammes (trigram_repetition)
Un trigramme est une suite de trois lemmes consécutifs. Dans une fenêtre de {windows}, chaque mot est d’abord remplacé par son lemme contextuel : `marche`, `marches` et `marchent` employés comme verbes deviennent ainsi `marcher`, tandis que le nom dans `la marche` reste `marche`. spaCy désambiguïse la catégorie grâce à la phrase ; Morphalou sert de repli lorsque cette analyse contextuelle est indisponible. Le programme compte les trigrammes distincts présents plus d’une fois, puis divise ce nombre par le nombre total de trigrammes distincts. Il s’agit donc d’une proportion de types répétés, et non de toutes les occurrences répétées.

# Redondance locale des trigrammes / Renouvellement local des trigrammes (moving_trigram_repetition)
Même proportion de trigrammes de lemmes distincts répétés, calculée dans des fenêtres glissantes de 300 mots espacées de 50 mots, puis moyennée. Cette version privilégie les formulations qui reviennent à proximité dans une fenêtre de {windows}, .

# Densité des noms / Sparcité des noms (noun_ratio)
Nombre de mots classés comme noms par Morphalou, divisé par le nombre total de mots auxquels Morphalou attribue une catégorie grammaticale. Les quatre lignes noms, verbes, adjectifs et adverbes ne totalisent pas nécessairement 100 %, car le dénominateur comprend aussi d’autres catégories.

# Densité des Verbes / Sparcité des verbes (verb_ratio)
Nombre de mots classés comme verbes par Morphalou, divisé par le nombre total de mots auxquels Morphalou attribue une catégorie grammaticale.

# Densité des adjectifs / Sparcité des adjectifs (adjective_ratio)
Nombre de mots classés comme adjectifs par Morphalou, divisé par le nombre total de mots auxquels Morphalou attribue une catégorie grammaticale.

# Densité des adverbes / Sparcité des adverbes (adverb_ratio)
Nombre de mots classés comme adverbes par Morphalou, divisé par le nombre total de mots auxquels Morphalou attribue une catégorie grammaticale.

# **Compressibilité gzip** / Incompressibilité gzip (gzip_compression_ratio)
Le texte UTF-8 est compressé avec gzip. La taille compressée est divisée par la taille originale et affichée en pourcentage. Une valeur basse signifie que les octets du texte sont plus prévisibles et se compressent mieux. Pour comparer les documents, le programme utilise des blocs non chevauchants ayant exactement {window}.

# **Densité de relatives et subordonnées** / Sparcité de relatives et subordonnées (relative_clause_ratio)
spaCy compte les dépendances de relative (`acl:relcl`) et les autres dépendances subordonnées configurées (`acl`, `advcl`, `ccomp`, `csubj`, `xcomp`). Leur somme est divisée par le nombre de phrases. La valeur peut dépasser 100 % : une phrase peut contenir plusieurs subordonnées. Ce résultat dépend de l’analyse du modèle spaCy.

# Densité de phrases nominales / Sparcité de phrases nominales (nominal_sentence_ratio)
Part des phrases dans lesquelles spaCy ne trouve aucun verbe conjugué. Les infinitifs et participes isolés ne suffisent pas à rendre la phrase verbale. La mesure repère notamment des ruptures comme « Un cauchemar. Encore un. », mais dépend de la qualité de l’analyse syntaxique.

# **Densité de voix active** / Densité de voix passive (active_voice_ratio)
Pourcentage des phrases du document contenant une construction verbale active et aucune construction passive. Le passif est reconnu par une dépendance `aux:pass`, un sujet `nsubj:pass` ou la marque morphologique `Voice=Pass`. La présence de l’auxiliaire « être » ne suffit pas : dans « il était allé », « était » construit un temps composé actif. 100 % signifie que toutes les phrases sont verbales et actives. Cette mesure est calculée sur le document entier, sans fenêtre.

# Densité de métaphores / Sparcité de métaphores (metaphorical_comme_ratio)
Pourcentage des phrases du document contenant au moins une comparaison détectée. Le programme reconnaît les « comme » comparatifs ainsi que les locutions inscrites dans `assets/dictionnaires/comparison-markers.txt`. « Il courait comme un chien enragé » et « Il courait comme Charlot courait » sont comptés ; « Comme il pleuvait, il restait chez lui » ne l’est pas. 100 % signifie que chaque phrase contient au moins une comparaison. Cette mesure est calculée sur le document entier, sans fenêtre. Elle repère une forme comparative, sans pouvoir garantir que l’image soit sémantiquement une métaphore.

# **Complexité syntaxique** / Minimalisme syntaxique (average_syntactic_depth)
Mesure la complexité hiérarchique des phrases reconnue par spaCy. Plus des groupes et propositions sont emboîtés les uns dans les autres, plus les mots les plus éloignés nécessitent de relations pour rejoindre le verbe principal, et plus la profondeur augmente.

L'idée : une phrase simple (« Le chat dort ») a une profondeur faible — un seul niveau entre le mot et le verbe. Une phrase à subordonnées empilées (« Le chat que le voisin, qui venait d'emménager, avait recueilli dormait ») a une profondeur élevée — plusieurs relations à traverser pour remonter jusqu'au verbe principal.

# Minimalisme flexionnel / Variation flexionnelle (form_lemma_ratio)
Dans chaque fenêtre mobile de 300 mots, la diversité des formes graphiques est divisée par la diversité des lemmes. Un ratio proche de 1 signifie que chaque lemme n'apparaît quasiment que sous une seule forme (peu de variation flexionnelle : toujours "marche", jamais "marchait" ou "marchions"). Un ratio élevé signifie qu'un même lemme revient sous de nombreuses formes différentes (le texte varie les temps, les nombres, les genres pour une même racine).

# **Taux d'hapax** / Taux de récurrence (hapax_ratio)
Nombre de lemmes lexicaux Morphalou apparaissant exactement une fois, divisé par le nombre de lemmes lexicaux distincts.

Un taux élevé signifie que le texte introduit beaucoup de mots qu'il n'utilise ensuite plus jamais (vocabulaire riche et non répété, parfois signe d'un style très varié ou au contraire de rareté statistique) ; un taux bas signifie que le vocabulaire lexical est concentré sur peu de lemmes, réemployés souvent.

# **Diversité de longueurs de phrase** / Uniformité des longueur de phrase  (sentence_word_std_dev)
Dans la fenêtre {windows}, écart-type du nombre de mots par phrase. Une valeur élevée indique une alternance plus forte entre phrases courtes et longues. La diversité des structures intègre déjà une partie de cette information en accordant progressivement davantage de poids aux phrases contenant plusieurs propositions. 

# Couverture stylistique (note_coverage)

Surface sur le graphique radar en fonction des valeurs affichées. C'est une signature stylistique et non un critère de qualité.

Pour rendre les axes comparables, le radar établit ses repères une seule fois sur tout le corpus, jamais sur la sélection affichée. La valeur est d'abord située linéairement entre le minimum et le maximum du corpus, puis transformée par une courbe logarithmique `log(1 + 4x) / log(5)`. Cette courbe continue étale les valeurs basses et ralentit progressivement l'approche de 100 %, sans supprimer ni saturer brutalement aucune œuvre. La transformation s'applique aux coordonnées du radar et au calcul de sa surface, sans modifier les valeurs brutes des tableaux.

Ce tassemment modère l'influence des choix stylistiques extrêmes, comme les phrases très longues qui mécaniquement tirent beaucoup d'indices à la hausse.

# Mots (word_count)
Nombre total de mots relevés dans le document analysé.

# Diversité des lemmes (unique_word_count)
Nombre de lemmes distincts divisé par le nombre total de mots du document. Les flexions d’un même lemme sont regroupées. La valeur est comprise entre 0 et 1.

# Phrases (sentence_count)
Nombre total de phrases relevées dans le document analysé.

# Paragraphes (paragraph_count)
Nombre total de paragraphes relevés dans le document analysé.

# Longueur moyenne des mots (caractères) (avg_word_length)
Nombre moyen de caractères par mot dans le document analysé.

# Longueur moyenne des phrases (caractères) (avg_sentence_length)
Nombre moyen de caractères par phrase dans le document analysé.

# Longueur moyenne des phrases (mots) (avg_sentence_word_count)
Nombre moyen de mots par phrase dans le document analysé.

# Longueur médiane des phrases (caractères) (median_sentence_length)
Longueur en caractères qui partage les phrases en deux groupes de même effectif.

# Longueur P10 des phrases (caractères) (sentence_length_p10)
Longueur en caractères sous laquelle se trouvent 10 % des phrases.

# Longueur P90 des phrases (sentence_length_p90)
Longueur en caractères sous laquelle se trouvent 90 % des phrases.

# Écart-type des paragraphes (paragraph_length_std_dev)
Écart-type du nombre de mots par paragraphe. Il mesure la dispersion des longueurs de paragraphes autour de leur moyenne.

# Caractères (document_char_count)
Nombre total de caractères du document analysé, espaces et retours à la ligne compris.

# Singularité (sentence_length_amplitude)
Distance de Burrows calculée sur trente-deux mesures stylistiques. Chaque mesure est d’abord centrée et réduite sur l’ensemble du corpus ; la distance entre deux œuvres est la moyenne des écarts absolus entre leurs z-scores. Le graphique affiche, pour chaque œuvre ou auteur sélectionné, la distance à son voisin le plus proche. Une valeur faible indique une proximité statistique, pas une identité d’auteur ni une preuve d’influence. Cette vue répond à la question « ce texte est-il isolé ou proche d’un autre ? » ; elle ne suffit pas à attribuer une ressemblance à un auteur.

# Carte stylistique MDS (sentence_length_std_dev)
Projection en deux dimensions des distances de Burrows calculées sur trente-deux mesures. Les œuvres proches dans la carte sont proches dans l’espace multidimensionnel ; les axes de la projection n’ont pas de signification littéraire propre. Le stress indique la part de déformation introduite par la réduction à deux dimensions : plus il est faible, plus la carte respecte les distances originales.

# Voisinage stylistique (type_token_ratio)
Pour l’œuvre choisie, les œuvres les plus proches sont classées par percentile décroissant. L’axe affiche le percentile de proximité dans toutes les distances du corpus : 90 % signifie que l’œuvre est plus proche que 90 % des paires comparées. Le titre du tableau donne directement le nombre de voisins par auteur. Les couleurs identifient les auteurs ; l’auteur de référence est affiché en couleur pleine afin que le nombre de voisins du même auteur soit immédiatement lisible. Une œuvre peut être épinglée pour apparaître en ligne supplémentaire, avec son rang réel dans le classement. Ces repères sont descriptifs et ne constituent pas une preuve d’attribution.

Mathématiquement, chaque œuvre est représentée par le vecteur de ses mesures sélectionnées. Pour chaque mesure `j`, on calcule sur tout le corpus la moyenne `μⱼ` et l’écart-type `σⱼ`, puis le score centré-réduit `zⱼ = (xⱼ − μⱼ) / σⱼ`. La distance entre deux œuvres `A` et `B` est la moyenne des écarts absolus sur les `p` mesures : `d(A,B) = (1/p) × Σ |zAⱼ − zBⱼ|`. Les voisins sont ensuite triés par distance croissante. Le percentile affiché est la proportion des distances du corpus qui sont supérieures à cette distance, multipliée par 100.

# Diversité lexicale mobile (moving_type_token_ratio)
Moyenne du rapport entre formes distinctes et mots dans les fenêtres lexicales du texte.

# Richesse globale des lemmes (global_lemma_richness)
Nombre de lemmes lexicaux distincts divisé par le nombre total de mots lexicaux du document.

# Richesse locale des lemmes (lemma_richness)
Moyenne du rapport entre lemmes distincts et mots lexicaux dans les fenêtres du texte.

# Couverture Morphalou (morphalou_coverage)
Part des formes lexicales reconnues et lemmatisées par Morphalou.

# Mots lexicaux (lexical_word_count)
Nombre de mots lexicaux retenus après exclusion des mots-outils.

# Lemmes distincts (unique_lemma_count)
Nombre de lemmes lexicaux distincts relevés dans le document.

# Longueur moyenne des paragraphes (avg_paragraph_length)
Nombre moyen de mots par paragraphe.

# Répétition des structures (structural_repetition_rate)
Part des signatures syntaxiques de phrases déjà rencontrées dans le texte.

# Propositions relatives (relative_clause_count)
Nombre de propositions relatives reconnues par spaCy.

# Propositions subordonnées (subordinate_clause_count)
Nombre de propositions subordonnées reconnues par spaCy.

# Densité de subordonnées (subordinate_clause_ratio)
Nombre moyen de propositions subordonnées par phrase.

# Phrases nominales (nominal_sentence_count)
Nombre de phrases dans lesquelles spaCy ne trouve aucun verbe conjugué.

# Noms communs spaCy (pos_common_noun_ratio)
Part des noms communs dans la distribution grammaticale calculée par spaCy.

# Noms propres spaCy (pos_proper_noun_ratio)
Part des noms propres dans la distribution grammaticale calculée par spaCy.

# Verbes spaCy (pos_verb_ratio)
Part des verbes dans la distribution grammaticale calculée par spaCy.

# Adjectifs spaCy (pos_adjective_ratio)
Part des adjectifs dans la distribution grammaticale calculée par spaCy.

# Adverbes spaCy (pos_adverb_ratio)
Part des adverbes dans la distribution grammaticale calculée par spaCy.

# Lisibilité de Flesch (flesch)
Indice de lisibilité adapté au français à partir de la longueur des phrases et du nombre de syllabes par mot.

# **Densité de participes présents** / Sparcité de participes présents (present_participle_ratio)
Part des formes verbales identifiées comme participes présents (`VerbForm=Part`, `Tense=Pres`) parmi les mots analysés. Elles sont séparées des verbes conjugués.

# **Densité de participes passés** / Sparcité de participes passés (past_participle_ratio)
Part des formes verbales identifiées comme participes passés (`VerbForm=Part`, `Tense=Past`) parmi les mots analysés. Un participe employé comme adjectif est compté dans les adjectifs, pas ici.

# **Passé simple** / Présence du passé simple (simple_past_ratio)
Part des verbes finis à l’indicatif passé, sans auxiliaire, parmi les verbes finis. Elle mesure l’emploi d’une forme narrative classique, indépendamment de l’âge du texte.

# **Subjonctif imparfait ou plus-que-parfait** / Subjonctif littéraire (literary_subjunctive_ratio)
Part des verbes finis au subjonctif imparfait ou plus-que-parfait parmi les verbes finis. Le subjonctif présent n’est pas compté.

# **Négations complètes** / Négations sans « ne » (negation_completeness_ratio)
Part des marqueurs négatifs détectés qui sont précédés d’un « ne » dans la même phrase. La mesure porte uniquement sur les négations repérées, et « ne...que » est exclu.

# **Futur périphrastique** / Futur simple (periphrastic_future_ratio)
Part des futurs employés qui sont construits avec « aller » au présent suivi d’un infinitif. Elle est calculée parmi les futurs détectés, pas sur l’ensemble du texte.

# **Familiarité orale** / Registre soutenu (oral_familiarity_ratio)
Occurrences de mots et expression fammilières. La liste est modifiable dans `assets/dictionnaires/familiarity-markers.txt`. Les marqueurs directs comptent partout ; les marqueurs positionnels ne comptent qu’en incise ou en fin de proposition.

# **Classique** / Contemporain (classicism_score)
Score qui agrège l'usage du passé simple, des subjonctifs imparfaits ou plus-que-parfaits, l'absence de futur périphrastique, l'absence de familiarité orale en dehors des dialogues, la diversité syntaxique, un style verbal et une voix active. Ce score est calibré sur le corpus, avec 100 % attribué à l'œuvre la plus « classique ».

# **Modificateurs par nom** (avg_modifiers_per_noun)
Nombre moyen de modificateurs directement rattachés aux noms (adjectif qualificatif : « une maison blanche » ; complément du nom : « une maison de pierre » ; proposition relative : « une maison qui domine la vallée »).

# **Noms fortement modifiés** (heavily_modified_noun_ratio)
Part des noms portant au moins deux modificateurs directs (voir modificateurs par nom).

# **Rareté lexicale** (lexical_rarity_score)
Moyenne de `-log10` des fréquences Lexique383. Une valeur élevée indique un vocabulaire moins fréquent ; Lexique383 ne distingue pas le vocabulaire littéraire du vocabulaire technique.

# **Chaînes adjectivales** (adjective_chain_ratio)
Nombre de chaînes d’adjectifs coordonnés rapporté au nombre de phrases.

# **Longueur des chaînes adjectivales** (avg_adjective_chain_length)
Nombre moyen d’adjectifs dans les chaînes coordonnées détectées.

# **Maximaliste** / Minimaliste (baroque_score)
Score composite : proche de 0, minimalisme ; proche de 1, maximalisme. Il combine l'enrichissement des groupes nominaux, les comparaisons, les chaînes adjectivales, la longueur des phrases, la profondeur d'expansion en fin de phrase, la densité d'incises, l'accumulation de coordinations et la densité de ponctuations savantes.

# **Verbes d’action** (action_verb_ratio)
Part des verbes finis qui ne figurent pas dans `assets/dictionnaires/stative-verbs.txt`. Certains verbes de cognition peuvent avoir un emploi événementiel ponctuel.

# **Connecteurs temporels** (temporal_connector_ratio)
Occurrences de connecteurs temporels ou séquentiels par phrases.

# **Sujets personnels** (personal_subject_ratio)
Part des sujets grammaticaux identifiables comme personnels. `on` et les noms communs animés ambigus sont exclus.

<!-- Note conservée pour référence historique : la mesure n’est plus calculée ni exposée. -->
# **Passé narratif** (narrative_past_ratio)
Part des verbes finis narratifs au passé, hors dialogues.

# **Narratif** / Descriptif (narrativity_score)
Score composite : proche de 1, récit d'action ; proche de 0, peinture descriptive. Il combine les verbes d'action, les connecteurs temporels, les dialogues, la voix active, le taux de rupture temporelle entre paragraphes et la densité de noms propres, en retirant les phrases nominales et l'accumulation d'adjectifs. Le passé narratif et le taux de marqueurs de sommaire restent des mesures informatives séparées et n'entrent pas dans ce score.

# **Dialogue** (dialogue_ratio)
Part des mots appartenant aux paragraphes dont le premier caractère (hors espaces) est un tiret cadratin, un tiret demi-cadratin ou un guillemet ouvrant. Ces paragraphes sont pris comme un seul bloc, sans découpage des répliques internes. Les mesures de temps, de négation et de futur de Classicism excluent ces phrases ; la familiarité orale les conserve.

# **Négativité** / Positivité (negation_ratio)
 Pourcentage de phrases contenant au moins un marqueur de négation (`ne`, `pas`, `plus`, `jamais`, etc.) : phrases négatives divisées par le nombre total de phrases. Cette mesure décrit le rapport négativité/positivité ; les dialogues sont inclus.

# Mots émotionnels (emotion_word_ratio)
Part des mots lexicaux dont le lemme figure dans le lexique FEEL (French Expanded Emotion Lexicon). Le lexique ne tient pas compte du contexte ni de la négation : « peur » est compté de la même façon dans une phrase affirmative ou négative. Source : http://advanse.lirmm.fr/feel.php.

# Verbes de réaction affective (affect_verb_ratio)
Part des verbes finis appartenant à `assets/dictionnaires/affect-verbs.txt` (pleurer, trembler, rire, etc.). Ces manifestations ponctuelles complètent le vocabulaire émotionnel.

# Densité d'interjections émotionnelles (interjection_density)
Occurrences des interjections définies dans `assets/dictionnaires/emotional-interjections.txt`, divisées par le nombre total de mots. Les expressions les plus longues sont reconnues en premier afin qu'une occurrence de « mon Dieu » ne compte pas aussi « Dieu » séparément.

# Intensificateurs devant adjectif (intensifier_adjective_ratio)
Part des adjectifs immédiatement précédés ou syntaxiquement modifiés (`advmod`) par un adverbe d'intensité tel que « si », « tellement », « extrêmement » ou « terriblement ».

# Noms de manifestation somatique (somatic_reaction_noun_ratio)
Part des noms communs dont le lemme figure dans `assets/dictionnaires/somatic-nouns.txt` (larmes, sueur, frisson, sanglot, soupir, tremblement, palpitation, etc.).

# Densité de points de suspension (ellipsis_ratio)
Occurrences de « … » ou « ... » rapportées au nombre total de phrases. Les trois points consécutifs forment une seule occurrence.

# Points d'interrogation hors dialogue (question_mark_narration_ratio)
Nombre de points d'interrogation situés hors des plages de dialogue, rapporté au nombre de phrases narratives. Cette mesure vise les questions portées par la voix narrative plutôt que les échanges conversationnels.

# Exclamations (exclamation_ratio)
Nombre de points d’exclamation rapporté au nombre de phrases. Cette mesure repère la ponctuation expressive, sans interpréter le contenu.

# Constructions exclamatives (exclamative_construction_ratio)
Part des phrases terminées par un point d’exclamation et commençant par « que », « comme », « quel » ou une forme apparentée. Elle cible les tournures exclamatives littéraires ; les autres exclamations restent comptées par la mesure précédente.

# **Émotionnel** / Neutre (emotionality_score)
Score agrégé des exclamations, points de suspension, questions portées par la narration et adjectifs modifiés par un intensificateur. Il décrit une densité d’expression affective explicite, pas la qualité ni la valence positive ou négative du texte. Les noms somatiques et interjections émotionnelles restent disponibles comme mesures exploratoires mais n’entrent pas dans ce score.
# Connecteurs logiques (logical_connector_ratio)
Occurrences de connecteurs logiques ou argumentatifs rapportées au nombre de phrases. Les marqueurs sont définis dans `assets/dictionnaires/logical-connectors.txt`.

# Noms abstraits (abstract_noun_ratio)
Part des noms communs dont la forme se termine par un suffixe fréquent de nominalisation abstraite (`-tion`, `-isme`, `-ité`, etc.). Il s’agit d’une approximation orthographique : elle peut classer à tort des noms concrets comme « voiture ».

# Présent gnomique (gnomic_present_ratio)
Part des verbes finis au présent de l’indicatif dont le sujet est générique ou abstrait, hors dialogues. Le calcul utilise le type de sujet, et non le seul temps verbal ; un présent de narration avec « il » n’est donc pas compté comme gnomique.

# **Discursif** / Immersif (discursivite_score)
Score fondé sur la densité des connecteurs logiques et argumentatifs, la part de noms abstraits et le présent gnomique. Une valeur élevée indique davantage de commentaire, de généralisation ou d'argumentation ; une valeur faible correspond à une scène plus directement vécue ou décrite.

# Temps littéraires (literary_tense_ratio)
Part des verbes finis narratifs au passé simple ou au subjonctif imparfait ou plus-que-parfait, hors dialogues. Cette mesure informative est utilisée comme composante du registre classique.

# Densité de noms propres (proper_noun_density)
Part des tokens non ponctuels et non espacés étiquetés `PROPN` par spaCy. Elle indique la place des personnes, lieux, marques et autres noms propres dans le texte.

# Noms concrets (concrete_noun_ratio)
Part des noms communs qui ne portent pas un suffixe de nominalisation abstraite. Les exceptions lexicales de `assets/dictionnaires/concrete-noun-exceptions.txt` sont retirées du calcul ; la liste est issue de Lexique383 et peut être enrichie manuellement.

# Taux de rupture temporelle (tense_shift_rate)
Proportion de transitions entre paragraphes consécutifs où le temps verbal dominant change. Les paragraphes sans verbe ne sont pas pris en compte ; une valeur élevée indique davantage d’alternance entre régimes temporels.

# Taux de marqueurs de sommaire (scene_summary_ratio)
Score moyen, calculé phrase par phrase, qui ne monte que si une phrase contient un mot ou une expression d'une liste fixe (« souvent », « chaque jour », « pendant des années », « avait l'habitude de »… définie dans `assets/dictionnaires/duration-markers.txt`) tout en étant nettement plus courte que la phrase la plus longue du corpus. Signale un sommaire narratif selon Genette : le récit qui condense une longue durée en peu de mots — par opposition à la scène, qui déploie un moment précis en détail.

# Densité d'incises (incise_density)
Proportion de phrases contenant au moins une proposition ou un groupe encadré par des virgules, des parenthèses ou des tirets cadratin ou demi-cadratin, inséré dans le fil syntaxique principal sans en être le sujet ou l'objet direct. La détection s'appuie sur les dépendances spaCy (`appos`, `acl:relcl`, `advcl` ou `parataxis`) lorsqu'une virgule précède le groupe. Une valeur élevée indique une phrase plus interrompue et enrichie ; une valeur faible, une phrase plus nue.

# Densité de ponctuation savante (punctuation_variety_score)
Nombre de points-virgules et de deux-points rapporté au nombre total de phrases du document. Ces signes explicitent ou déploient une articulation logique ou énumérative à l'intérieur de la phrase ; une valeur élevée indique une syntaxe plus élaborée.

# Taux de modalité généralisante (modal_generalization_ratio)
Part des verbes qui sont des modaux (`devoir`, `pouvoir`, `falloir`) dont le sujet est générique ou impersonnel, notamment « on » ou « il » impersonnel. La liste des verbes est définie dans `assets/dictionnaires/modal_verbs.txt`. Une valeur élevée signale un discours qui énonce des règles ou des vérités générales, plutôt qu'un récit d'événements situés.

# Taux d'accumulation coordonnée (coordination_accumulation_ratio)
Proportion de phrases comportant plus de deux coordinations syntaxiques (`dep_ == "cc"`), par exemple des enchaînements avec « et » ou « puis ». Seules les coordinations identifiées par spaCy sont comptées, pas les virgules seules. Une valeur élevée capte une écriture par énumération ou accumulation ; une valeur faible correspond à des phrases qui tranchent davantage.

# Profondeur d'expansion finale (right_branching_depth)
Profondeur syntaxique moyenne du sous-arbre dont la tête est le dernier mot de chaque phrase. La mesure suit les liens de dépendance de ce dernier mot vers la racine, en restant dans la phrase. Une valeur élevée indique que la phrase continue à se ramifier vers sa fin ; elle complète la profondeur syntaxique moyenne, qui porte sur toute la phrase.
