import ast
import sqlite3
import tempfile
import unittest
from pathlib import Path

from detector.config import NON_PERSISTED_METRICS, METRICS, PERSISTED_METRICS
from detector.analyse import analyse_file, build_html as build_analysis_html, repetition_highlights
from detector.epub_database import metric_cache_is_valid, reset_champ
from detector.metrics import cached_metric_values
from detector.stats import Metrics, _bigram_count, _hapax_bigram_count, _trigram_lemmas, normalize_markdown_text
from detector.web_export import ensure_nonempty_export, missing_export_fields, site_config
from burstiness.render_html import build_html as build_burstiness_html
from burstiness.cli import generate as generate_burstiness_html


class MetricsTests(unittest.TestCase):
    def test_empty_web_export_is_rejected_when_database_has_books(self):
        with self.assertRaises(ValueError):
            ensure_nonempty_export(1, [])
        ensure_nonempty_export(0, [])

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

    def test_hapax_bigrams_use_contextual_lemmas_over_the_whole_document(self):
        contextual = [
            ("marche", "marcher", "verbe", 0, 6),
            ("marche", "marche", "nom", 7, 13),
            ("marche", "marcher", "verbe", 14, 20),
        ]
        self.assertEqual(_trigram_lemmas(["marche"] * 3, contextual), ["marcher", "marche", "marcher"])
        self.assertEqual(_bigram_count(["a", "b", "a", "b", "c"]), 3)
        self.assertEqual(_hapax_bigram_count(["a", "b", "a", "b", "c"]), 2)
        metrics = Metrics("Texte sans importance")
        metrics.__dict__["trigram_lemma_values"] = ["a", "b", "a", "b", "c"]
        self.assertEqual(metrics.bigram_count(), 3)
        self.assertEqual(metrics.hapax_bigram_count(), 2)
        self.assertEqual(metrics.hapax_bigram_ratio(), 2 / 3)
        connection = sqlite3.connect(":memory:")
        connection.execute("CREATE TABLE metric_cache (book_id INTEGER, window_index INTEGER, metric_name TEXT, value_json TEXT)")
        connection.executemany(
            "INSERT INTO metric_cache VALUES (1,0,?,?)",
            [("bigram_count", "3"), ("hapax_bigram_count", "2")],
        )
        self.assertEqual(cached_metric_values(connection, 1)["hapax_bigram_ratio"], 2 / 3)

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

    def test_burstiness_cli_uses_source_name_in_wip_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "roman.md"
            source.write_text("Phrase courte. Autre phrase.", encoding="utf-8")
            output = generate_burstiness_html(source, Path(directory) / "out")
            self.assertEqual(output.name, "roman-burst.html")
            self.assertTrue(output.is_file())

    def test_repetition_analysis_groups_inflected_forms_and_reuses_colors(self):
        text = (
            "La chambre jouxte plusieurs chambres. Je veux faire ce qu'il faisait et ce que vous faisiez. "
            + "…" * 1600 + " Une route rejoint deux routes."
        )
        highlights = repetition_highlights(text, 1500)
        marked = [(text[start:end].casefold(), lemma, color) for start, end, lemma, color in highlights]
        self.assertEqual([word for word, _lemma, _color in marked], ["chambre", "chambres", "faire", "faisait", "faisiez", "route", "routes"])
        self.assertEqual({lemma for word, lemma, _color in marked if word.startswith("chambre")}, {"chambre"})
        self.assertEqual({lemma for word, lemma, _color in marked if word in {"faire", "faisait", "faisiez"}}, {"faire"})
        self.assertNotIn(marked[0][2], {color for word, _lemma, color in marked if word in {"faire", "faisait", "faisiez"}})
        self.assertEqual(marked[0][2], marked[-1][2])
        rendered = build_analysis_html(text, "repetitions", "Test")
        self.assertIn("répétitions lexicales à 1500 caractères", rendered)
        self.assertIn('data-group="faire"', rendered)
        self.assertIn('mark.selected { background: #111 !important; color: white; }', rendered)
        self.assertNotIn("cursor: help", rendered)

    def test_analysis_omits_yaml_front_matter_and_names_metric(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "roman.md"
            source.write_text("---\ntitle: Secret\n---\n\nLa chambre rejoint les chambres.", encoding="utf-8")
            output = analyse_file(source, "repetitions", Path(directory) / "out")
            rendered = output.read_text(encoding="utf-8")
            self.assertEqual(output.name, "roman_repetitions.html")
            self.assertNotIn("title: Secret", rendered)
            self.assertIn("La <mark", rendered)

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
        text = "Il est grand, élancé et vif."
        self.assertEqual(Metrics(text).ternary_count(), 1)
        rendered = build_analysis_html(text, "ternary_count", "Test")
        self.assertIn(">Il est grand, élancé et vif.</mark>", rendered)
        self.assertEqual(Metrics("Il court, saute et danse.").ternary_count(), 1)
        self.assertEqual(Metrics("Il parle doucement, clairement et calmement.").ternary_count(), 1)
        self.assertEqual(Metrics("L'homme qui court, qui saute et qui danse.").ternary_count(), 1)
        self.assertEqual(Metrics("Il est grand et vif.").ternary_count(), 0)
        self.assertEqual(Metrics("Il est grand, élancé, vif et calme.").ternary_count(), 0)
        self.assertEqual(Metrics(
            "Je ne veux pas m'apitoyer, seulement lui être utile, une troisième béquille sur laquelle elle peut s'appuyer à la moindre défaillance."
        ).ternary_count(), 0)
        self.assertEqual(Metrics("Nous n'étions dupes ni l'un ni l'autre.").ternary_count(), 0)
        self.assertEqual(Metrics("Le passé m'attire, rassurant, familier.").ternary_count(), 0)
        self.assertEqual(Metrics('Je ne garantis rien.» Je la récupère, épuisée, découragée.').ternary_count(), 0)
        self.assertEqual(Metrics(
            "Devant Isa ensanglantée, j'ai réagi mécaniquement, privé d'émotions intempestives."
        ).ternary_count(), 0)
        self.assertEqual(Metrics("C'est la vie, merveilleuse et fragile.").ternary_count(), 0)
        self.assertEqual(Metrics('Je lui ferme les yeux.«Bye bye, Isa.» Ou plutôt:').ternary_count(), 0)
        self.assertEqual(Metrics("Nous regardions l'étang, encore et encore.").ternary_count(), 0)
        self.assertEqual(Metrics(
            "Accorder notre attention à la nature pour délivrer notre esprit du souci de soi.»"
        ).ternary_count(), 0)

    def test_structure_and_tricolons_share_frames_and_nested_nominal_groups(self):
        text = "Dans la rue, devant le pont, il regarde la mer, le ciel et les arbres."
        metrics = Metrics(text)
        self.assertEqual(metrics.structures, ["CADRATIF , CADRATIF , SUJET VERBE , NOM , NOM , NOM ."])
        self.assertEqual([text[start:end] for start, end in metrics.ternary_ranges], ["la mer, le ciel et les arbres."])
        self.assertEqual(metrics.ternary_count(), metrics.syntax["ternary_count"])
        continuation = "Il est fils de marin, né à Paris, élevé au goût du sel, du rhum clair et de l'école publique."
        self.assertEqual(Metrics(continuation).ternary_count(), 0)

    def test_structure_removes_attached_elaboration_and_compares_hinges(self):
        text = "Il était sec, maigre, tordu comme un arbre qui a grandi dans le vent."
        metrics = Metrics(text)
        self.assertEqual(metrics.structures, ["SUJET VERBE COMPLÉMENT , COMPLÉMENT , COMPLÉMENT ."])
        self.assertEqual([text[start:end] for start, end in metrics.ternary_ranges], ["Il était sec, maigre, tordu"])
        repeated = "Il reste, comme si la vie revenait, comme si la nuit tombait, comme si le jour naissait."
        self.assertEqual(Metrics(repeated).ternary_count(), 1)
        different = repeated.replace("comme si la nuit tombait", "quand la nuit tombait")
        self.assertEqual(Metrics(different).ternary_count(), 0)

    def test_ternary_groups_of_six_and_document_boundaries(self):
        text = "Il parle, il marche, il chante, elle rit, elle danse, elle rêve."
        metrics = Metrics(text)
        self.assertEqual(metrics.ternary_count(), 2)
        self.assertEqual([text[start:end] for start, end in metrics.ternary_ranges], ["Il parle, il marche, il chante", "elle rit, elle danse, elle rêve."])
        bounded = "# sec, maigre, grand\n\nsec, maigre\n\ngrand\n\nIl est sec, maigre, grand."
        self.assertEqual(Metrics(bounded).ternary_count(), 1)
        for empty in ("", "!", "# titre"):
            with self.subTest(text=empty):
                self.assertEqual(Metrics(empty).ternary_count(), 0)

    def test_structural_measures_compare_roles_instead_of_vocabulary(self):
        regular = Metrics("Le chat dort. Le chien dort.")
        self.assertEqual(regular.structural_diversity(), 0)
        self.assertEqual(regular.structural_rhythm(), 0)
        self.assertEqual(regular.structural_repetition_rate(), 1)
        varied = Metrics("Le chat dort. Quand la nuit tombe, nous ouvrons la porte.")
        self.assertGreater(varied.structural_diversity(), 0)
        self.assertGreater(varied.structural_rhythm(), 0)

    def test_mechanical_antithesis_requires_matching_pos_patterns(self):
        self.assertEqual(
            Metrics("Il défend non seulement une décision difficile, mais aussi une mesure injuste.").mechanical_antithesis_count(),
            1,
        )
        self.assertEqual(
            Metrics("Il défend non seulement une décision difficile, mais aussi rapidement.").mechanical_antithesis_count(),
            0,
        )
        metrics = Metrics("")
        metrics.mechanical_antithesis_count = lambda: 2
        metrics.stereotype_count = lambda: 3
        metrics.epistemic_hedging_count = lambda: 4
        metrics.sentence_count = lambda: 10
        self.assertEqual(metrics.mechanical_antithesis_ratio(), 0.2)
        self.assertEqual(metrics.stereotype_ratio(), 0.3)
        self.assertEqual(metrics.epistemic_hedging_ratio(), 0.4)

    def test_stereotype_count_uses_lemmas_and_avoids_nested_matches(self):
        text = "Il serra les poings. Elle serre les dents. Il avait le souffle court."
        metrics = Metrics(text)
        self.assertEqual(metrics.stereotype_count(), 3)
        rendered = build_analysis_html(text, "stereotype_count", "Test")
        self.assertEqual(rendered.count("<mark "), 3)
        self.assertIn("data-distance=", rendered)
        self.assertIn("Précédente : — · Suivante : +", rendered)
        self.assertIn("serra les poings</mark>", rendered)
        self.assertIn('id="next-highlight"', rendered)
        self.assertIn('id="highlight-distance"', rendered)
        self.assertIn("scrollIntoView", rendered)

    def test_epistemic_hedging_count_uses_fixed_marker_phrases(self):
        metrics = Metrics("On pourrait dire que oui. À certains égards, cela dit, rien n'est certain.")
        self.assertEqual(metrics.epistemic_hedging_count(), 3)
        rendered = build_analysis_html(metrics.text, "epistemic_hedging_count", "Test")
        self.assertEqual(rendered.count("<mark "), 3)
        self.assertIn(">On pourrait dire que</mark>", rendered)

    def test_stereotypes_filter_function_words_and_keep_longest_match(self):
        for text, expected in (
            ("Son cœur cognait dans sa poitrine.", "cœur cognait dans sa poitrine"),
            ("Elle serrait ses poings de douleur.", "serrait ses poings de douleur"),
            ("Ses yeux se remplirent de larmes.", "yeux se remplirent de larmes"),
        ):
            with self.subTest(text=text):
                metrics = Metrics(text)
                self.assertEqual(metrics.stereotype_count(), 1)
                self.assertEqual([text[start:end] for start, end in metrics.stereotype_ranges], [expected])
        for text in ("Il serra. Les poings restèrent immobiles.", "Il serra doucement les poings."):
            with self.subTest(text=text):
                self.assertEqual(Metrics(text).stereotype_count(), 0)

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
