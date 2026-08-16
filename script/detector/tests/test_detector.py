import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from detector.config import OUTPUT_DIR, SOURCE_DIR
from detector.stats_cli import display_name, markdown_comparison, markdown_lemma_report, markdown_stats, output_paths as stats_output_paths


class DetectorTests(unittest.TestCase):
    def test_stats_report_names(self):
        markdown, json = stats_output_paths(Path("exemple.md"))
        self.assertEqual(markdown, OUTPUT_DIR / "exemple_stats.md")
        self.assertEqual(json, OUTPUT_DIR / "exemple_stats.json")

    def test_comparison_uses_filenames_as_columns(self):
        sources = sorted(SOURCE_DIR.glob("*.md"))
        report = markdown_comparison(sources)
        self.assertIn("| Mesure | " + " | ".join(display_name(source) for source in sources) + " | Δ[^1] |", report)
        self.assertIn("| IA[^2] |", report)
        self.assertIn("| Diversité syntaxique[^3] |", report)
        self.assertRegex(report, r"\| IA\[\^2\] \| (?:\d+ %|indisponible)")
        self.assertRegex(report, r"\| Diversité syntaxique\[\^3\] \| \d+ %")
        self.assertNotIn("Richesse lexicale globale", report)
        self.assertNotIn("Mots lexicaux", report)
        self.assertNotIn("Richesse comparable", report)
        self.assertIn("La burstiness est", report)
        self.assertIn("répétition des structures", report)
        self.assertIn("## Synthèse", report)
        self.assertIn("## Détails", report)
        self.assertIn("Répétitions stylistiques[^14]", report)
        self.assertIn("Répétitions lexicales[^15]", report)
        self.assertIn("Répétitions familiales[^16]", report)
        self.assertIn("Répétitions sonores[^17]", report)
        self.assertIn("ne compte pas les déterminants", report)
        self.assertNotIn("score heuristique", report)
        self.assertIn("Diversité lemmatisée", report)
        self.assertRegex(report, r"\| Burstiness\[\^13\] \| \d+,\d{2}")
        self.assertRegex(report, r"\| Répétitions stylistiques\[\^14\] \| \d+,\d %")
        summary, details = report.split("## Détails", 1)
        self.assertNotIn("| Mots[^33] |", summary)
        self.assertIn("| Mots[^33] |", details)
        self.assertIn("| Lisibilité Flesch[^32] |", details)
        self.assertNotIn("| Lisibilité Flesch[^32] |", summary)
        self.assertNotIn("| Amplitude (caractères)[^11] |", summary)
        self.assertIn("| Amplitude (caractères)[^11] |", details)
        self.assertNotIn("| Mots-outils[^18] |", summary)
        self.assertIn("| Mots-outils[^18] |", details)
        self.assertNotIn("| Noms[^19] |", summary)
        self.assertIn("| Noms[^19] |", details)
        self.assertNotIn("| Verbes[^20] |", summary)
        self.assertIn("| Verbes[^20] |", details)
        self.assertNotIn("| Adjectifs[^21] |", summary)
        self.assertIn("| Adjectifs[^21] |", details)
        self.assertNotIn("| Adverbes[^22] |", summary)
        self.assertIn("| Adverbes[^22] |", details)
        self.assertIn("| Diversité syntaxique[^3] |", summary)
        self.assertNotIn("| Diversité syntaxique[^3] |", details)
        self.assertNotIn("| Répétitions stylistiques[^14] |", summary)
        self.assertIn("| Répétitions stylistiques[^14] |", details)
        self.assertIn("| Répétition des structures[^4] |", summary)
        self.assertNotIn("| Répétition des structures[^4] |", details)
        self.assertIn("| Diversité des structures[^5] |", summary)
        self.assertNotIn("| Rythme des structures[^23] |", summary)
        self.assertIn("| Rythme des structures[^23] |", details)
        self.assertNotIn("| Compression gzip[^24] |", summary)
        self.assertIn("| Compression gzip[^24] |", details)
        self.assertIn("| Relatives et subordonnées[^6] |", summary)
        self.assertRegex(summary, r"\| Relatives et subordonnées\[\^6\] \| (?:\d+ %|indisponible)")
        self.assertRegex(summary, r"\| Relatives et subordonnées\[\^6\] \| .* \| \d+,\d % \|")
        self.assertIn("| Ponctuation (signes/300 mots)[^7] |", summary)
        self.assertIn("| Diversité de ponctuation[^9] |", summary)
        self.assertIn("| Variété des débuts de phrase[^10] |", summary)
        self.assertIn("| Phrases nominales[^8] |", summary)
        self.assertNotIn("| Écart-type des paragraphes (mots)[^43] |", summary)
        self.assertNotIn("| Phrases nominales[^8] |", details)
        self.assertNotIn("Burstiness des paragraphes", report)
        self.assertIn("| Écart-type des paragraphes (mots)[^43] |", details)
        self.assertNotIn("| Profondeur syntaxique[^25] |", summary)
        self.assertIn("| Profondeur syntaxique[^25] |", details)
        self.assertIn("## Répartition grammaticale par document", report)
        self.assertIn("![Répartition grammaticale](grammatical_distribution.svg)", report)
        self.assertNotIn("| Noms propres |", report)
        self.assertNotIn("| Catégorie | Part |", report)
        self.assertIn("| Écart-type des phrases (caractères)[^42] |", details)
        self.assertNotIn("Lisibilité Flesch française", report)
        self.assertNotRegex(report, r"(?m)^\| .*points d’uniformité")
        self.assertIn("| Variation des phrases (mots)[^12] |", report)
        self.assertIn("| Longueur moyenne des phrases (mots)[^38] |", report)
        self.assertIn("| Diversité des formes[^26] |", report)
        self.assertIn("| Diversité lemmatisée[^27] |", report)
        self.assertIn("| Mots employés une seule fois[^28] |", report)
        self.assertIn("| Répétition globale des trigrammes[^29] |", report)
        self.assertIn("| Répétition locale des trigrammes[^30] |", report)
        self.assertIn("| Taux de répétition non filtré[^31] |", report)
        self.assertIn("Répétition des structures[^4]", report)
        self.assertIn("| Diversité de ponctuation[^9] |", report)
        self.assertIn("| Variété des débuts de phrase[^10] |", report)
        self.assertNotIn("Plus longue série de phrases proches", report)
        self.assertIn("| Noms[^19] |", report)
        self.assertIn("| Verbes[^20] |", report)
        self.assertIn("| Adjectifs[^21] |", report)
        self.assertRegex(report, r"\| Compression gzip\[\^24\] \| .* \| \d+,\d % \|")
        self.assertRegex(report, r"\| Mots\[\^33\] \| .* \| — \|")
        self.assertGreater(details.index("| Mots[^33] |"), details.index("| Lisibilité Flesch[^32] |"))
        self.assertGreater(details.index("| Fenêtres de répétition analysées[^44] |"), details.index("| Lisibilité Flesch[^32] |"))
        statistical_tables = report.split("## Répartition grammaticale", 1)[0]
        measure_lines = [
            line for line in statistical_tables.splitlines()
            if line.startswith("| ") and not line.startswith("| Mesure") and not line.startswith("|---")
        ]
        self.assertTrue(all(re.match(r"\| .+\[\^\d+\] \|", line) for line in measure_lines))

    def test_single_markdown_report_has_summary_and_details(self):
        from detector.stats import compute_stats, uniformity_score
        source = sorted(SOURCE_DIR.glob("*.md"))[0]
        stats = compute_stats(source.read_text(encoding="utf-8"))
        report = markdown_stats(source, stats, uniformity_score(stats))
        self.assertIn("## Synthèse", report)
        self.assertIn("## Détails", report)
        self.assertIn("Répétitions stylistiques[^13]", report)

    def test_stylistic_repetition_matches_reference_order(self):
        from detector.stats import compute_stats
        values = {
            stem: compute_stats((SOURCE_DIR / f"{stem}.md").read_text(encoding="utf-8")).stylistic_repetition_rate
            for stem in ("lettre1", "lettre2", "reponse")
        }
        self.assertGreater(values["lettre1"], values["reponse"])
        self.assertAlmostEqual(values["lettre1"], .096, delta=.01)
        self.assertAlmostEqual(values["lettre2"], .152, delta=.01)
        self.assertAlmostEqual(values["reponse"], .064, delta=.01)

    def test_source_display_names(self):
        self.assertEqual(display_name(Path("lettre1.md")), "Lettre 1")
        self.assertEqual(display_name(Path("mon_roman-12.md")), "Mon roman 12")

    def test_range_is_normalized_by_possible_or_observed_maximum(self):
        from detector.stats_cli import normalized_range
        self.assertEqual(normalized_range(["10 %", "20 %"]), "10,0 %")
        self.assertEqual(normalized_range(["0 %", "1 %", "0 %"]), "0,5 %")
        self.assertEqual(normalized_range(["10", "20"]), "50,0 %")

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
        from detector.stats import structural_diversity, structural_rhythm
        signatures = ["SUJET VERBE .", "SUJET VERBE .", "VERBE COMPLÉMENT ."]
        self.assertAlmostEqual(structural_diversity(signatures), 2 / 3)
        self.assertEqual(structural_diversity(["INCONNU .", "SUJET VERBE ."]), .5)
        self.assertGreater(structural_rhythm(signatures), 0)
        self.assertEqual(structural_rhythm(["SUJET VERBE .", "SUJET VERBE ."]), 0)

    def test_uniformity_uses_all_diversity_signals(self):
        from detector.stats import TextStats, uniformity_components
        components = uniformity_components(TextStats(avg_sentence_length=50, sentence_length_amplitude=50))
        self.assertEqual(set(components), {
            "sentence_amplitude", "burstiness", "vocabulary_repetition",
            "structure_repetition", "structure_similarity", "structure_rhythm",
        })

    def test_ai_score_v1_formula(self):
        from detector.stats import TextStats, ai_score
        stats = TextStats(
            burstiness=.83, gzip_compression_ratio=.52,
            structural_diversity=.60, filtered_repetition_rate=.10,
            relative_clause_ratio=0, subordinate_clause_ratio=1,
        )
        self.assertIsInstance(ai_score(stats), int)

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
        report = markdown_lemma_report(SOURCE_DIR / "reponse.md")
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

    def test_dynamic_lemma_windows_cover_the_end(self):
        from detector.stats import lemma_richness_distribution
        distribution = lemma_richness_distribution(["fleur", "fleurs", "maison", "maisons"] * 100, 200, 50)
        self.assertEqual(distribution["count"], 5)


if __name__ == "__main__": unittest.main()
