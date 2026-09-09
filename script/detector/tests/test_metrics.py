import ast
import sqlite3
import unittest
from pathlib import Path

from detector.config import ANALYSIS_WINDOW_WORDS, NON_PERSISTED_METRICS, METRICS, PERSISTED_METRICS
from detector.epub_database import word_windows
from detector.epub_database import metric_cache_is_valid, reset_champ
from detector.metrics import windowed_metric_fields
from detector.stats import Metrics, normalize_markdown_text, tokenize


class MetricsTests(unittest.TestCase):
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

    def test_analysis_windows_contain_one_thousand_words(self):
        self.assertEqual(ANALYSIS_WINDOW_WORDS, 1_000)
        text = " ".join(f"mot{index}" for index in range(2_100))
        self.assertEqual([len(tokenize(fragment)) for _, _, fragment in word_windows(text)], [1_000, 1_000, 100])

    def test_lexical_window_ratios_use_the_whole_analysis_window(self):
        metrics = Metrics("chat chat chien")
        self.assertEqual(metrics.moving_type_token_ratio(), 2 / 3)
        self.assertEqual(metrics.lemma_richness(), metrics.global_lemma_richness())

    def test_local_ratio_averages_every_thousand_word_block(self):
        first = ["meme"] * 1_000
        second = [f"mot{index}" for index in range(1_000)]
        metrics = Metrics(" ".join(first + second))
        self.assertAlmostEqual(metrics.moving_type_token_ratio(), (1 / 1_000 + 1) / 2)
        self.assertEqual(windowed_metric_fields(), set())

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

    def test_punctuation_total_is_the_sum_of_detailed_counts(self):
        metrics = Metrics('. , : ; ! ? … - – — () « » “ ” "')
        detailed = (
            metrics.period_count(), metrics.comma_count(), metrics.colon_count(), metrics.semicolons_count(),
            metrics.exclamation_point_count(), metrics.question_mark_count(), metrics.suspention_point_count(),
            metrics.dash_count(), metrics.parenthesis_count(), metrics.quote_mark_count(),
        )
        self.assertEqual(metrics.dash_count(), 2)
        self.assertEqual(metrics.punctuation_mark_count(), sum(detailed))

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
