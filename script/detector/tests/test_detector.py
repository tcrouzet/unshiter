import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from detector.config import OUTPUT_DIR, SOURCE_DIR
from detector.syntax_depth import analyze_syntax, dialogue_char_ranges
from detector.stats import (ellipsis_ratio, interjection_density, emotion_sentence_ratio,
                            emotion_intensification_ratio,
                            emotion_category_profile,
                            question_mark_ratio)
from detector.stats_cli import (
    comparison_sources,
    comparison_documents,
    corpus_fingerprint,
    display_name,
    markdown_comparison,
    markdown_lemma_report,
    markdown_stats,
    notes,
    kiviat_chart,
    detail_kiviat_profiles,
    normalize_source_text,
    output_paths as stats_output_paths,
    read_source,
)


class DetectorTests(unittest.TestCase):
    def test_emotional_sentences_match_single_and_multiword_lemmas_once(self):
        sentences = [("il", "rire", "et", "sourire"), ("il", "fondre", "en", "larme"), ("xyz", "abc")]
        self.assertEqual(emotion_sentence_ratio(sentences), 2 / 3)

    def test_emotional_intensification_uses_emotional_lemma_denominator(self):
        class Token:
            def __init__(self, lemma, index, dep=""):
                self.lemma_, self.i, self.dep_ = lemma, index, dep
                self.is_alpha, self.children = True, []

        doc = [Token("très", 0), Token("triste", 1), Token("joie", 2),
               Token("xyz", 3, "amod"), Token("peur", 4)]
        doc[2].children.append(doc[3])
        self.assertEqual(emotion_intensification_ratio(doc), 2 / 3)

    def test_emotional_category_profile_uses_dictionary_sections(self):
        profile = emotion_category_profile([("joie", "et", "tristesse")])
        self.assertEqual(profile["joie"], 0.5)
        self.assertEqual(profile["tristesse"], 0.5)
        self.assertAlmostEqual(profile["entropy"], 1.0)

    def test_exploratory_emotional_punctuation_metrics(self):
        text = "Pourquoi partir ?\n\n— Tu pars ?\n\nIl reste..."
        ranges = dialogue_char_ranges(text)
        self.assertEqual(ellipsis_ratio(text, 3), 1 / 3)
        self.assertEqual(question_mark_ratio(text, 3), 2 / 3)

    def test_interjections_do_not_double_count_multiword_markers(self):
        self.assertEqual(interjection_density("Ah, mon Dieu !", 3), 2 / 3)

    def test_dialogue_is_excluded_from_classicism_narrative_counters(self):
        narrative = analyze_syntax("Il chanta.")
        mixed = analyze_syntax("Il chanta.\n\n— Il chanta.")
        self.assertEqual(dialogue_char_ranges("Il chanta.\n\n— Il chanta."), [(12, 24)])
        self.assertEqual(narrative["simple_past"], mixed["simple_past"])
        self.assertGreater(mixed["dialogue_ratio"], 0)

    def test_present_homographs_are_not_counted_as_simple_past(self):
        text = ("La maison ne frémit pas. Elle agit ainsi avec tous. "
                "J'accours, oubliant l'interdit d'entrer. "
                "Ses sourires nous déchirent. Elle ne réagit pas.")
        self.assertEqual(analyze_syntax(text)["simple_past"], 0)

    def test_unambiguous_simple_past_is_still_counted(self):
        self.assertEqual(analyze_syntax("Il chanta puis partit.")["simple_past"], 2)

    def test_dialogue_ratio_is_zero_for_narration(self):
        self.assertEqual(analyze_syntax("Il marche dans la rue.")["dialogue_ratio"], 0)
    def test_editorial_comments_are_injected_in_markdown_source(self):
        rendered = "\n".join(notes(["Diversité des structures"]))
        self.assertIn("[^1]:", rendered)
        self.assertIn("<!-- Proposition de Codex", rendered)
        self.assertIn("La diversité des longueurs entre directement", rendered)

    def test_stats_report_names(self):
        markdown, json = stats_output_paths(Path("exemple.md"))
        self.assertEqual(markdown, OUTPUT_DIR / "exemple_stats.md")
        self.assertEqual(json, OUTPUT_DIR / "exemple_stats.json")

    def test_comparison_uses_filenames_as_columns(self):
        sources = comparison_sources()
        report = markdown_comparison(sources)
        self.assertNotIn(" %", report)
        self.assertIn("\u00a0%", report)
        report = report.replace("\u00a0", " ")
        displayed_sources = [source for source, _ in comparison_documents(sources)]
        self.assertIn("| Mesure | " + " | ".join(display_name(source) for source in displayed_sources) + " | σ[^1] |", report)
        self.assertRegex(report, r"(?m)^\[\^1\]: .+")
        self.assertNotRegex(report, r"(?m)^\| IA(?:\[\^\d+\])? \|")
        self.assertNotIn("Rang IA", report)
        self.assertNotIn("Diversité syntaxique", report)
        self.assertNotIn("Richesse lexicale globale", report)
        self.assertNotIn("Mots lexicaux", report)
        self.assertNotIn("Richesse comparable", report)
        self.assertIn("moyenne(|longueur suivante", report)
        self.assertNotIn("| Répétition des structures", report)
        self.assertIn("## Synthèse", report)
        self.assertIn("## Détails", report)
        self.assertRegex(report, r"Diversité stylistique\[\^\d+\]")
        self.assertRegex(report, r"Répétitions lexicales\[\^\d+\]")
        self.assertRegex(report, r"Répétitions familiales\[\^\d+\]")
        self.assertRegex(report, r"Répétitions sonores\[\^\d+\]")
        self.assertIn("Les mots-outils", report)
        summary, details = report.split("## Détails", 1)
        self.assertNotIn("| Mots |", summary)
        self.assertIn("| Mots |", details)
        self.assertNotIn("Lisibilité Flesch", report)
        self.assertRegex(summary, r"\| Ratio noms/verbes\[\^\d+\] \| \d+\.\d{2}")
        self.assertRegex(details, r"\| Formes par lemme\[\^\d+\] \| \d+\.\d{2}")
        self.assertNotIn("| Diversité de longueurs de phrase (mots)", summary)
        self.assertRegex(details, r"\| Diversité de longueurs de phrase \(mots\)\[\^\d+\] \|")
        self.assertNotIn("| Compression gzip", summary)
        self.assertIn("| Diversité des débuts de phrase", summary)
        self.assertIn("| Burstiness", summary)
        self.assertNotIn("| Répétitions stylistiques", report)
        self.assertRegex(summary, r"\| Diversité des structures\[\^\d+\] \|")
        self.assertNotIn("Burstiness des paragraphes", report)
        self.assertIn("| Écart-type des paragraphes (mots) |", details)
        self.assertRegex(summary, r"\| Profondeur syntaxique\[\^\d+\] \|")
        self.assertIn("## Profil comparatif", report)
        self.assertIn("![Diagramme de Kiviat](kiviat.svg)", report)
        self.assertIn("## Répartition grammaticale par document", report)
        self.assertIn("![Répartition grammaticale](grammatical_distribution.svg)", report)
        self.assertNotIn("| Noms propres |", report)
        self.assertNotIn("| Catégorie | Part |", report)
        self.assertNotIn("Écart-type des phrases (caractères)", report)
        self.assertIn("| Longueur moyenne des phrases (mots) |", report)
        self.assertNotIn("Plus longue série de phrases proches", report)
        self.assertGreater(details.index("| Mots |"), details.index("Répétitions non filtrées"))
        self.assertGreater(details.index("| Fenêtres analysées |"), details.index("Répétitions non filtrées"))
        self.assertIn("| Longueur moyenne des paragraphes (mots) |", details)

    def test_single_markdown_report_has_summary_and_details(self):
        from detector.stats import compute_stats
        source = sorted(SOURCE_DIR.glob("*.md"))[0]
        stats = compute_stats(read_source(source))
        report = markdown_stats(source, stats)
        self.assertNotIn(" %", report)
        self.assertIn("\u00a0%", report)
        report = report.replace("\u00a0", " ")
        self.assertIn("## Synthèse", report)
        self.assertIn("## Détails", report)
        self.assertRegex(report, r"Diversité stylistique\[\^\d+\]")

    def test_stylistic_repetition_detects_repeated_content(self):
        from detector.stats import compute_stats
        repetitive = compute_stats("Le marin regarde la mer. " * 40).stylistic_repetition_rate
        varied = compute_stats("Le marin observe la mer puis rejoint le port. Une tempête surprend son équipage.").stylistic_repetition_rate
        self.assertGreater(repetitive, varied)

    def test_source_normalization_collapses_excess_blank_lines(self):
        self.assertEqual(normalize_source_text("un\n\ndeux"), "un\n\ndeux")
        self.assertEqual(normalize_source_text("un\n\n\n\n deux"), "un\n\n deux")
        self.assertEqual(normalize_source_text("un\r\n\r\n\r\ndeux"), "un\n\ndeux")

    def test_source_display_names(self):
        self.assertEqual(display_name(Path("lettre1.md")), "Lettre 1")
        self.assertEqual(display_name(Path("_Crouzet.md")), "Crouzet")
        self.assertEqual(display_name(Path("mon_roman-12.md")), "Mon roman 12")

    def test_comparison_sources_put_ai_before_alphabetical_humans(self):
        sources = comparison_sources()
        human_index = next((index for index, source in enumerate(sources) if source.stem.startswith("_")), len(sources))
        self.assertTrue(all(not source.stem.startswith("_") for source in sources[:human_index]))
        self.assertTrue(all(source.stem.startswith("_") for source in sources[human_index:]))
        self.assertEqual(
            [display_name(source) for source in sources[human_index:]],
            sorted((display_name(source) for source in sources[human_index:]), key=str.casefold),
        )

    def test_ai_sources_are_merged_into_one_document(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ai_b = root / "second.md"
            human = root / "_Humain.md"
            ai_a = root / "premier.md"
            ai_a.write_text("Premier texte IA.", encoding="utf-8")
            ai_b.write_text("Second texte IA.", encoding="utf-8")
            human.write_text("Texte humain.", encoding="utf-8")
            documents = comparison_documents([ai_a, ai_b, human])
        self.assertEqual([source.name for source, _ in documents], ["IA.md", "_Humain.md"])
        self.assertEqual(documents[0][1], "Premier texte IA.\n\nSecond texte IA.")

    def test_corpus_fingerprint_changes_with_source_content(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "texte.md"
            source.write_text("Première version.", encoding="utf-8")
            first = corpus_fingerprint([source])
            source.write_text("Deuxième version.", encoding="utf-8")
            second = corpus_fingerprint([source])
        self.assertNotEqual(first, second)

    def test_dispersion_is_standard_deviation_over_mean(self):
        from detector.stats_cli import coefficient_dispersions
        rows = [[("Mesure", "10")], [("Mesure", "20")], [("Mesure", "30")]]
        self.assertEqual(coefficient_dispersions(rows)["Mesure"], "40.8 %")

    def test_dispersion_ignores_tukey_outlier(self):
        from detector.stats_cli import coefficient_dispersions
        rows = [[("Mesure", str(value))] for value in (.1, .3, .3, .5, .7, 1.6)]
        self.assertEqual(coefficient_dispersions(rows)["Mesure"], "53.7 %")

    def test_kiviat_always_contains_noun_verb_ratio(self):
        from detector.stats import TextStats
        analyses = [
            (Path("IA.md"), TextStats(noun_verb_ratio=1.5, structural_diversity=.2, structural_rhythm=.3, sentence_word_std_dev=4, punctuation_per_300_words=30, punctuation_diversity=.3, stylistic_repetition_rate=.1, function_word_ratio=.4, form_lemma_ratio=.9, gzip_compression_ratio=.4)),
            (Path("_Auteur.md"), TextStats(noun_verb_ratio=2.2, structural_diversity=.8, structural_rhythm=.7, sentence_word_std_dev=12, punctuation_per_300_words=60, punctuation_diversity=.7, stylistic_repetition_rate=.2, function_word_ratio=.3, form_lemma_ratio=.98, gzip_compression_ratio=.5)),
        ]
        self.assertIn("Ratio noms/verbes", kiviat_chart(analyses))

    def test_detail_kiviat_only_keeps_dispersed_detail_measures(self):
        from detector.stats import TextStats
        analyses = [
            (Path(f"texte{index}.md"), TextStats(trigram_repetition=index / 100))
            for index in range(1, 7)
        ]
        dimensions, _ = detail_kiviat_profiles(analyses)
        self.assertIn("Répétition globale des trigrammes", [dimension[0] for dimension in dimensions])
        trigram_dimension = next(dimension for dimension in dimensions if dimension[0] == "Répétition globale des trigrammes")
        self.assertTrue(trigram_dimension[4])
        self.assertNotIn("Diversité de longueurs de phrase (mots)", [dimension[0] for dimension in dimensions])
        self.assertNotIn("Mots", [dimension[0] for dimension in dimensions])

    def test_windows_do_not_overlap_and_end_on_paragraphs(self):
        from detector.stats_cli import source_windows
        paragraphs = ["mot " * 6, "suite " * 6, "fin " * 6]
        windows = source_windows("\n\n".join(paragraphs), 10, minimum_final_ratio=.5)
        self.assertEqual(len(windows), 2)
        self.assertNotIn("fin", windows[0])
        self.assertIn("fin", windows[1])

    def test_short_final_window_is_discarded(self):
        from detector.stats_cli import source_windows
        paragraphs = ["mot " * 10, "reste " * 3]
        windows = source_windows("\n\n".join(paragraphs), 10, minimum_final_ratio=.7)
        self.assertEqual(len(windows), 1)
        self.assertNotIn("reste", windows[0])

    def test_only_short_window_is_still_analyzed(self):
        from detector.stats_cli import source_windows
        self.assertEqual(source_windows("court texte", 10), ["court texte"])

    def test_gzip_windows_have_equal_byte_lengths(self):
        from detector.stats_cli import byte_windows
        windows = byte_windows("é" * 20, 10)
        self.assertTrue(windows)
        self.assertTrue(all(len(window) == 10 for window in windows))

    def test_equivalent_sentence_structures_are_repeated(self):
        from detector.stats import sentence_structure_signatures, structural_repetition_rate
        signatures = sentence_structure_signatures([
            "Quand il se lève, il chante.",
            "Quand il mange, il rigole.",
        ])
        self.assertEqual(signatures[0], signatures[1])
        self.assertEqual(structural_repetition_rate(signatures), 1)
        self.assertEqual(signatures[0], "PROPOSITION_SUBORDONNÉE , SUJET VERBE .")

    def test_only_comma_and_period_are_kept_in_structures(self):
        from detector.stats import sentence_structure_signatures
        statement, question = sentence_structure_signatures(["Il chante.", "Il chante ?"])
        self.assertEqual(statement, "SUJET VERBE .")
        self.assertEqual(question, "SUJET VERBE")
        self.assertTrue(statement.endswith("."))

    def test_line_break_ends_a_structure(self):
        from detector.stats import split_structure_units
        self.assertEqual(split_structure_units("Yannick,\nJe réponds."), ["Yannick,", "Je réponds."])

    def test_only_blank_line_starts_a_new_paragraph(self):
        from detector.stats import compute_stats
        self.assertEqual(compute_stats("Première ligne\nSeconde ligne").paragraph_count, 1)
        self.assertEqual(compute_stats("Premier paragraphe\n\nSecond paragraphe").paragraph_count, 2)

    def test_pour_infinitive_is_a_subordinate_clause(self):
        from detector.stats import sentence_structure_signatures
        long, short = sentence_structure_signatures([
            "Je fais un effort pour ne pas te balancer une réponse lapidaire.",
            "Tu m’as posé une question.",
        ])
        self.assertEqual(long, "SUJET VERBE COMPLÉMENT PROPOSITION_SUBORDONNÉE .")
        self.assertEqual(short, "SUJET VERBE COMPLÉMENT .")

    def test_structural_diversity_and_rhythm(self):
        from detector.stats import structural_diversity, structural_rhythm, structural_subpatterns
        signatures = ["SUJET VERBE .", "SUJET VERBE .", "VERBE COMPLÉMENT ."]
        self.assertGreater(structural_diversity(signatures), 0)
        self.assertLess(structural_diversity(signatures), 2 / 3)
        self.assertEqual(structural_diversity(["INCONNU .", "SUJET VERBE ."]), 0)
        chained = "SUJET VERBE COMPLÉMENT PROPOSITION_SUBORDONNÉE PROPOSITION_SUBORDONNÉE ."
        self.assertEqual(structural_subpatterns(chained), [
            "SUJET VERBE COMPLÉMENT", "PROPOSITION_SUBORDONNÉE", "PROPOSITION_SUBORDONNÉE",
        ])
        self.assertGreater(structural_diversity([
            chained, chained, "SUJET VERBE COMPLÉMENT .",
        ]), 0)
        self.assertGreater(structural_rhythm(signatures), 0)
        self.assertEqual(structural_rhythm(["SUJET VERBE .", "SUJET VERBE ."]), 0)

    def test_repeated_subordinates_count_less_than_distinct_structures(self):
        from detector.stats import _structural_profile_distance
        simple = (("PRINCIPALE", 1), ("SUBORDONNÉE", 1))
        repeated = (("PRINCIPALE", 1), ("SUBORDONNÉE", 5))
        varied = tuple((f"STRUCTURE {index}", 1) for index in range(6))
        self.assertGreater(_structural_profile_distance(simple, repeated), 0)
        self.assertLess(
            _structural_profile_distance(simple, repeated),
            _structural_profile_distance(simple, varied),
        )

    def test_uniformity_uses_all_diversity_signals(self):
        from detector.stats import TextStats, uniformity_components
        components = uniformity_components(TextStats(avg_sentence_length=50, sentence_length_amplitude=50))
        self.assertEqual(set(components), {
            "sentence_amplitude", "burstiness", "vocabulary_repetition",
            "structure_repetition", "structure_similarity", "structure_rhythm",
        })

    def test_noun_verb_and_form_lemma_ratios(self):
        from detector.stats import TextStats
        stats = TextStats(noun_ratio=.4, verb_ratio=.2, moving_type_token_ratio=.9, lemma_richness=1.0)
        stats.noun_verb_ratio = stats.noun_ratio / stats.verb_ratio
        stats.form_lemma_ratio = stats.moving_type_token_ratio / stats.lemma_richness
        self.assertEqual(stats.noun_verb_ratio, 2)
        self.assertEqual(stats.form_lemma_ratio, .9)

    def test_lexical_window_is_300_words(self):
        from detector.config import LEXICAL_WINDOW_SIZE
        self.assertEqual(LEXICAL_WINDOW_SIZE, 300)

    def test_hapax_are_counted_on_morphalou_lemmas(self):
        from detector.stats import lemma_hapax_ratio
        self.assertEqual(lemma_hapax_ratio(["fleur", "fleurs", "arbre"]), .5)

    def test_active_voice_distinguishes_compound_past_from_passive(self):
        from detector.syntax_depth import analyze_syntax
        active = analyze_syntax("Il était allé à Paris.")
        passive = analyze_syntax("Le chien est poursuivi par le chat.")
        self.assertEqual(active["active_voice_ratio"], 1)
        self.assertEqual(passive["active_voice_ratio"], 0)

    def test_metaphorical_comme_excludes_circumstantial_clause(self):
        from detector.syntax_depth import analyze_syntax
        comparison = analyze_syntax("Il courait comme un chien enragé.")
        verbal_comparison = analyze_syntax("Il courait comme Charlot courait.")
        circumstance = analyze_syntax("Comme il pleuvait, il restait chez lui.")
        self.assertEqual(comparison["metaphorical_comme_ratio"], 1)
        self.assertEqual(verbal_comparison["metaphorical_comme_ratio"], 1)
        self.assertEqual(circumstance["metaphorical_comme_ratio"], 0)
        self.assertEqual(analyze_syntax("Il courait vite.")["metaphorical_comme_ratio"], 0)

    def test_comparison_phrases_are_counted_per_sentence(self):
        from detector.syntax_depth import analyze_syntax
        analysis = analyze_syntax(
            "Il parlait à la manière de son père. Elle avançait à la façon d'une reine. Rien ne bougeait."
        )
        self.assertAlmostEqual(analysis["metaphorical_comme_ratio"], 2 / 3)

    def test_repetitive_text_compresses_better(self):
        from detector.stats import compute_stats
        repetitive = compute_stats(("bonjour monde " * 200).strip())
        varied = compute_stats(" ".join(f"mot{index:04d}" for index in range(400)))
        self.assertLess(repetitive.gzip_compression_ratio, varied.gzip_compression_ratio)

    def test_punctuation_density_is_per_300_words(self):
        from detector.stats import compute_stats
        stats = compute_stats("mot, " * 100)
        self.assertAlmostEqual(stats.punctuation_per_300_words, 300)

    def test_long_repetition_metric_uses_fixed_windows(self):
        from detector.stats import compute_stats
        short = compute_stats(("alpha beta gamma delta epsilon " * 40) + ".")
        long = compute_stats((("alpha beta gamma delta epsilon " * 40) + ". ") * 10)
        self.assertAlmostEqual(short.moving_trigram_repetition, long.moving_trigram_repetition, places=2)

    def test_trigrams_group_morphalou_inflections(self):
        from detector.stats import compute_stats
        stats = compute_stats("Il marche vite. Il marchait vite.")
        self.assertGreater(stats.trigram_repetition, 0)

    def test_inflections_share_a_lemma_for_richness(self):
        from detector.morphalou import lemma_map
        lemmas = lemma_map(["fleur", "fleurs", "mange", "mangeaient"])
        self.assertEqual(lemmas["fleur"], lemmas["fleurs"])
        self.assertEqual(lemmas["mange"], lemmas["mangeaient"])

    def test_both_repetition_rates_group_inflections(self):
        from detector.stats import local_repetition_rate
        words = ["marche", "marches", "marchent"]
        self.assertGreater(local_repetition_rate(words, filtered=False), 0)
        self.assertGreater(local_repetition_rate(words, filtered=True), 0)

    def test_lemma_report_bolds_repeated_inflections(self):
        report = markdown_lemma_report(SOURCE_DIR / "IA.md")
        self.assertIn("**", report)

        from detector.stats import repetition_lemma_annotations
        self.assertEqual(
            repetition_lemma_annotations(["fleur", "fleurs", "fleur"]),
            [("fleur", True), ("fleur", True), ("fleur", True)],
        )

        from detector.demonette import family_map
        families = family_map(["écrire", "écrivain", "écriture", "démarche"])
        self.assertTrue(families["écrire"] & families["écrivain"])
        self.assertTrue(families["écrire"] & families["écriture"])
        self.assertFalse(families["écrire"] & families["démarche"])

    def test_context_distinguishes_etre_from_summer(self):
        from detector.stats import tokenize_repetitions
        tokens = tokenize_repetitions("Il était là. Ils étaient là. Il a été malade. L’été était chaud.")
        if tokens and isinstance(tokens[0], tuple):
            lemmas = [(token[0], token[1]) for token in tokens]
            self.assertEqual([lemma for word, lemma in lemmas if word in {"était", "étaient"}], ["être", "être", "être"])
            self.assertIn(("été", "être"), lemmas)
            self.assertIn(("été", "été"), lemmas)

    def test_three_repetition_modes(self):
        from detector.stats import local_repetition_rate, tokenize_repetitions
        tokens = tokenize_repetitions("Cette curiosité pourrait suffire. J’ai suffisamment attendu.")
        lexical = local_repetition_rate(tokens, filtered=True, mode="lexical")
        family = local_repetition_rate(tokens, filtered=True, mode="family")
        phonetic = local_repetition_rate(tokens, filtered=True, mode="phonetic")
        self.assertEqual(lexical, 0)
        self.assertEqual(family, 0)
        self.assertGreater(phonetic, 0)

if __name__ == "__main__": unittest.main()
