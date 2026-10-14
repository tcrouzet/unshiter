import ast
import sqlite3
import unittest
from pathlib import Path

from detector.config import NON_PERSISTED_METRICS, METRICS, PERSISTED_METRICS
from detector.epub_database import metric_cache_is_valid, reset_champ
from detector.metrics import cached_metric_values
from detector.stats import Metrics, normalize_markdown_text
from detector.web_export import missing_export_fields, site_config
from burstiness.render_html import build_html as build_burstiness_html


class MetricsTests(unittest.TestCase):
    def test_site_prompt_is_loaded_from_configured_file(self):
        site = site_config()
        self.assertIn("[PLACEHOLDER]", site["prompt_rewriting"])
        self.assertIn("[PLACEHOLDER]", site["prompt_writing"])
        self.assertNotEqual(site["prompt_rewriting"], site["prompt_writing"])

    def test_web_export_requires_every_non_composite_metric(self):
        values = {field: 0 for field in METRICS}
        values.pop("verb_count")
        self.assertEqual(missing_export_fields(values, {"classicism_score"}), ["verb_count"])
        values["verb_count"] = 1
        values["classicism_score"] = float("nan")
        self.assertEqual(missing_export_fields(values, {"classicism_score"}), [])

    def test_every_documented_metric_has_an_explicit_method(self):
        source = Path(__file__).resolve().parents[1] / "stats.py"
        module = ast.parse(source.read_text(encoding="utf-8"))
        metrics_class = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "Metrics")
        methods = {node.name for node in metrics_class.body if isinstance(node, ast.FunctionDef)}
        self.assertEqual([field for field in METRICS if field not in methods], [])

    def test_every_metric_can_be_called(self):
        metrics = Metrics('« Ah ! » dit-il. Il marche très vite — puis il sourit…')
        for field in METRICS:
            with self.subTest(field=field):
                getattr(metrics, field)()

    def test_derived_metrics_are_never_persisted(self):
        self.assertFalse(set(NON_PERSISTED_METRICS) & set(PERSISTED_METRICS))
        self.assertTrue({
            "classicism_score", "baroque_score", "narrativity_score",
            "emotionality_score", "discursivite_score",
        }.issubset(NON_PERSISTED_METRICS))

    def test_lexical_window_ratios_use_the_whole_analysis_window(self):
        metrics = Metrics("chat chat chien")
        self.assertEqual(metrics.moving_type_token_ratio(), 2 / 3)
        self.assertEqual(metrics.lemma_richness(), metrics.global_lemma_richness())

    def test_local_ratio_averages_every_thousand_word_block(self):
        first = ["meme"] * 1_000
        second = [f"mot{index}" for index in range(1_000)]
        metrics = Metrics(" ".join(first + second))
        self.assertAlmostEqual(metrics.moving_type_token_ratio(), (1 / 1_000 + 1) / 2)

    def test_sentence_start_diversity_uses_initial_structural_units(self):
        metrics = Metrics("")
        metrics.__dict__["structures"] = [
            "SUJET VERBE COMPLÉMENT , PROPOSITION_SUBORDONNÉE",
            "VERBE COMPLÉMENT . SUJET VERBE",
            "SUJET VERBE COMPLÉMENT ,",
        ]
        expected = ["SUJET VERBE COMPLÉMENT ,", "VERBE COMPLÉMENT .", "SUJET VERBE COMPLÉMENT ,"]
        self.assertEqual(metrics.sentence_start_structures, expected)
        self.assertAlmostEqual(metrics.sentence_start_diversity(), 2 / 3)
        self.assertEqual(metrics.sentence_start_recurrence_distance(), 2)

    def test_markdown_normalization_converts_ascii_ellipsis(self):
        self.assertEqual(normalize_markdown_text("Attends... vraiment...."), "Attends… vraiment…")

    def test_incise_count_includes_parentheses_and_paired_long_dashes(self):
        metrics = Metrics("Il part (sans attendre). Elle reste — bien sûr — ici.")
        self.assertEqual(metrics.incise_count(), 2)
        self.assertEqual(metrics.incise_ratio(), 1)

    def test_burstiness_count_matches_colored_html_sentences(self):
        text = "Chat dort. Paul court. Jean marche. Cette phrase est volontairement beaucoup plus longue que les précédentes."
        metrics = Metrics(text)
        self.assertEqual(metrics.burstiness_count(), build_burstiness_html(text).count('class="burst"'))
        self.assertAlmostEqual(metrics.burstiness_ratio(), 1 - metrics.burstiness_count() / metrics.sentence_count())
        self.assertEqual(metrics.burstiness_word(), metrics.burstiness() * metrics.avg_sentence_length())

    def test_punctuation_total_is_the_sum_of_detailed_counts(self):
        metrics = Metrics('. , : ; ! ? … - – — () « » “ ” "')
        detailed = (
            metrics.period_count(), metrics.comma_count(), metrics.colon_count(), metrics.semicolons_count(),
            metrics.exclamation_point_count(), metrics.question_mark_count(), metrics.suspention_point_count(),
            metrics.dash_count(), metrics.parenthesis_count(), metrics.quote_mark_count(),
        )
        self.assertEqual(metrics.dash_count(), 2)
        self.assertEqual(metrics.parenthesis_count(), 1)
        self.assertEqual(metrics.punctuation_mark_count(), sum(detailed))

        connection = sqlite3.connect(":memory:")
        connection.execute("CREATE TABLE metric_cache (book_id INTEGER, window_index INTEGER, metric_name TEXT, value_json TEXT)")
        fields = (
            "period_count", "comma_count", "colon_count", "semicolons_count",
            "exclamation_point_count", "question_mark_count", "suspention_point_count",
            "dash_count", "parenthesis_count", "quote_mark_count",
        )
        connection.executemany(
            "INSERT INTO metric_cache VALUES (1,0,?,?)",
            [(field, "1") for field in fields] + [("word_count", "20"), ("punctuation_mark_count", "999")],
        )
        values = cached_metric_values(connection, 1)
        self.assertEqual(values["punctuation_mark_count"], 10)
        self.assertEqual(values["punctuation_ratio"], 0.5)

    def test_dash_count_excludes_dialogue_openings(self):
        metrics = Metrics("— Première réplique. Texte – incise – suite. – Seconde réplique.")
        self.assertEqual(metrics.dash_count(), 2)

    def test_exclamation_count_excludes_dialogue(self):
        metrics = Metrics("« Stop ! » Il reste !")
        self.assertEqual(metrics.exclamation_point_count(), 2)

    def test_dialogue_count_uses_only_dash_opened_paragraphs(self):
        metrics = Metrics("« Citation seule. »\n\n— Réplique brève.")
        self.assertEqual(metrics.dialog_word_count(), 2)

    def test_ternary_count_requires_exactly_three_parallel_elements(self):
        self.assertEqual(Metrics("Il est grand, élancé et vif.").ternary_count(), 1)
        self.assertEqual(Metrics("Il court, saute et danse.").ternary_count(), 1)
        self.assertEqual(Metrics("Il parle doucement, clairement et calmement.").ternary_count(), 1)
        self.assertEqual(Metrics("L'homme qui court, qui saute et qui danse.").ternary_count(), 1)
        self.assertEqual(Metrics("Il est grand et vif.").ternary_count(), 0)
        self.assertEqual(Metrics("Il est grand, élancé, vif et calme.").ternary_count(), 0)

    def test_periphrastic_future_ratio_uses_sentence_count(self):
        metrics = Metrics("")
        metrics.va_count = lambda: 3
        metrics.present_participe_count = lambda: 3
        metrics.past_participe_count = lambda: 6
        metrics.simple_past_count = lambda: 6
        metrics.subjonctive_count = lambda: 2
        metrics.sentence_count = lambda: 12
        self.assertEqual(metrics.periphrastic_future_ratio(), 0.25)
        self.assertEqual(metrics.present_participle_ratio(), 0.25)
        self.assertEqual(metrics.past_participle_ratio(), 0.5)
        metrics.verb_count = lambda: 8
        self.assertEqual(metrics.simple_past_ratio(), 0.75)
        self.assertEqual(metrics.literary_subjunctive_ratio(), 1 / 6)
        connection = sqlite3.connect(":memory:")
        connection.execute("CREATE TABLE metric_cache (book_id INTEGER, window_index INTEGER, metric_name TEXT, value_json TEXT)")
        connection.executemany(
            "INSERT INTO metric_cache VALUES (1,0,?,?)",
            [("va_count", "3"), ("present_participe_count", "3"), ("past_participe_count", "6"), ("simple_past_count", "6"), ("subjonctive_count", "2"), ("sentence_count", "12"), ("verb_count", "12")],
        )
        values = cached_metric_values(connection, 1)
        self.assertEqual(values["periphrastic_future_ratio"], 0.25)
        self.assertEqual(values["present_participle_ratio"], 0.25)
        self.assertEqual(values["past_participle_ratio"], 0.5)
        self.assertEqual(values["simple_past_ratio"], 0.5)
        self.assertEqual(values["literary_subjunctive_ratio"], 1 / 6)

    def test_personal_subject_ratio_uses_classifiable_subjects(self):
        metrics = Metrics("")
        metrics.personal_subject_count = lambda: 3
        metrics.classifiable_subject_count = lambda: 4
        metrics.sentence_count = lambda: 12
        self.assertEqual(metrics.personal_subject_ratio(), 0.75)
        connection = sqlite3.connect(":memory:")
        connection.execute("CREATE TABLE metric_cache (book_id INTEGER, window_index INTEGER, metric_name TEXT, value_json TEXT)")
        connection.executemany(
            "INSERT INTO metric_cache VALUES (1,0,?,?)",
            [("personal_subject_count", "3"), ("classifiable_subject_count", "4"), ("sentence_count", "12")],
        )
        self.assertEqual(cached_metric_values(connection, 1)["personal_subject_ratio"], 0.75)

    def test_personal_subject_count_includes_impersonal_subjects_in_denominator(self):
        metrics = Metrics("Marie arrive. Nous restons. Il faut partir. La pluie tombe.")
        self.assertEqual(metrics.personal_subject_count(), 2)
        self.assertEqual(metrics.classifiable_subject_count(), 3)
        self.assertEqual(metrics.personal_subject_ratio(), 2 / 3)

    def test_first_person_subject_count_counts_sentences_including_dialogue(self):
        metrics = Metrics("Je pars. Nous restons ensemble. — Je reviens. Elle attend.")
        self.assertEqual(metrics.first_person_subject_count(), 3)
        self.assertEqual(metrics.first_person_subject_ratio(), 3 / 4)

    def test_grammatical_ratios_use_word_count(self):
        metrics = Metrics("")
        metrics.common_noun_count = lambda: 20
        metrics.proper_noun_count = lambda: 5
        metrics.grammatical_verb_count = lambda: 15
        metrics.adjective_count = lambda: 10
        metrics.adverb_count = lambda: 5
        metrics.abstract_noun_count = lambda: 8
        metrics.word_count = lambda: 100
        self.assertEqual(metrics.noun_ratio(), 0.25)
        self.assertEqual(metrics.verb_ratio(), 0.15)
        self.assertEqual(metrics.adjective_ratio(), 0.10)
        self.assertEqual(metrics.adverb_ratio(), 0.05)
        self.assertEqual(metrics.abstract_noun_ratio(), 0.08)

    def test_verb_tense_counts_use_finite_verbs(self):
        metrics = Metrics("Il mange. Il marchait. Il marchera. « Il parle. »")
        self.assertEqual(metrics.verb_imp_count(), 1)
        self.assertEqual(metrics.verb_fut_count(), 1)
        self.assertEqual(metrics.verb_present_count(), 2)
        self.assertEqual(metrics.verb_count(), 4)

    def test_passe_compose_includes_dialogue_and_excludes_passive_auxiliary(self):
        metrics = Metrics("Il a mangé. « Il a dormi. » Il est aimé.")
        self.assertEqual(metrics.passe_compose_count(), 2)
        self.assertEqual(metrics.verb_present_count(), 1)

    def test_metric_cache_validation_is_scoped_to_one_field(self):
        connection = sqlite3.connect(":memory:")
        connection.execute(
            "CREATE TABLE metric_cache (book_id INTEGER, window_index INTEGER, "
            "metric_name TEXT, value_json TEXT, content_sha256 TEXT, "
            "function_hash TEXT, updated_at TEXT)"
        )
        connection.execute(
            "INSERT INTO metric_cache VALUES (1,0,'word_count','3','document',?,?)",
            ("", "now"),
        )
        self.assertTrue(metric_cache_is_valid(connection, 1, "word_count", "document"))
        self.assertFalse(metric_cache_is_valid(connection, 1, "sentence_count", "document"))
        self.assertFalse(metric_cache_is_valid(connection, 1, "word_count", "modified-document"))

    def test_reset_champ_invalidates_only_the_requested_metric(self):
        connection = sqlite3.connect(":memory:")
        connection.execute("CREATE TABLE metric_cache (book_id INTEGER, metric_name TEXT)")
        connection.executemany(
            "INSERT INTO metric_cache VALUES (?,?)",
            [(1, "word_count"), (1, "sentence_count"), (2, "word_count")],
        )
        self.assertEqual(reset_champ(connection, "word_count"), 2)
        self.assertEqual(connection.execute("SELECT metric_name FROM metric_cache").fetchall(), [("sentence_count",)])


if __name__ == "__main__":
    unittest.main()
