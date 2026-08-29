"""Configuration centrale des répertoires et fichiers du projet."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
README_FILE = PROJECT_ROOT / "README.md"

SCRIPT_DIR = PROJECT_ROOT / "script"
SOURCE_DIR = PROJECT_ROOT / "sources"
EPUB_DIR = PROJECT_ROOT / "_epub"
OUTPUT_DIR = PROJECT_ROOT / "_output"
WEB_DIR = PROJECT_ROOT / "web"
WEB_DATA_FILE = WEB_DIR / "data.json"
ASSETS_DIR = PROJECT_ROOT / "assets"
SITE_CONFIG_FILE = ASSETS_DIR / "site.yml"
README_TEXTS_FILE = ASSETS_DIR / "readme-texts.md"
CHART_PALETTE_FILE = ASSETS_DIR / "chart-palette.yml"
PUBLICATION_FILE = ASSETS_DIR / "publication.yml"
WIKIPEDIA_CACHE_FILE = ASSETS_DIR / "wikipedia-cache.json"
EPUB_DATABASE = ASSETS_DIR / "unshiter.sqlite3"
EPUB_ANALYSIS_WINDOW_SIZE = 20_000
EPUB_ANALYSIS_VERSION = "first-window-clean-body-v53-weighted-axes"
TESTS_DIR = PROJECT_ROOT / "tests"
DOC_DIR = PROJECT_ROOT / "_doc"
TEMP_DIR = PROJECT_ROOT / "_temp"
EPUB_HASH_CACHE_FILE = TEMP_DIR / "epub-hashes.json"

DEFAULT_INPUT_FILE = SOURCE_DIR / "IA.md"
REPORT_FILENAME_SUFFIX = "_report"
STATS_FILENAME_SUFFIX = "_stats"
SOURCE_MARKDOWN_PATTERN = "*.md"
MARKDOWN_EXTENSION = ".md"
JSON_EXTENSION = ".json"
STATS_COMPARISON_FILE = OUTPUT_DIR / "stats_comparison.md"
MORPHALOU_DIR = ASSETS_DIR / "morphalou"
MORPHALOU_ARCHIVE = MORPHALOU_DIR / "Morphalou3.1_formatCSV_toutEnUn.zip"
MORPHALOU_CSV_MEMBER = "Morphalou3.1_formatCSV_toutEnUn/Morphalou3.1_CSV.csv"
MORPHALOU_INDEX = MORPHALOU_DIR / "morphalou.sqlite3"
FUNCTION_WORDS_FILE = ASSETS_DIR / "function-words.txt"
COMPARISON_MARKERS_FILE = ASSETS_DIR / "comparison-markers.txt"
FAMILIARITY_MARKERS_FILE = ASSETS_DIR / "familiarity-markers.txt"
NEGATION_COMPLETE_MARKERS_FILE = ASSETS_DIR / "negation-complete-markers.txt"
LEXIQUE_DIR = ASSETS_DIR / "lexique"
LEXIQUE_ARCHIVE = LEXIQUE_DIR / "Lexique383.tsv"
LEXIQUE_INDEX = LEXIQUE_DIR / "lexique.sqlite3"
STATIVE_VERBS_FILE = ASSETS_DIR / "stative-verbs.txt"
TEMPORAL_CONNECTORS_FILE = ASSETS_DIR / "temporal-connectors.txt"
LOGICAL_CONNECTORS_FILE = ASSETS_DIR / "logical-connectors.txt"
AFFECT_VERBS_FILE = ASSETS_DIR / "affect-verbs.txt"
FEEL_DIR = ASSETS_DIR / "feel"
FEEL_ARCHIVE = FEEL_DIR / "FEEL.csv"
FEEL_INDEX = FEEL_DIR / "feel.sqlite3"
STATS_NOTES_FILE = ASSETS_DIR / "stats-notes.md"
STRUCTURE_REPORT_SUFFIX = "_structure"
LEMMA_REPORT_SUFFIX = "_lemmes"
GRAMMATICAL_DISTRIBUTION_CHART = OUTPUT_DIR / "grammatical_distribution.svg"
KIVIAT_CHART = OUTPUT_DIR / "kiviat.svg"
KIVIAT_DETAIL_CHART = OUTPUT_DIR / "kiviat_details.svg"
README_KIVIAT_DETAIL_CHART = ASSETS_DIR / "readme" / "kiviat-details-github.png"
README_KIVIAT_CHART = ASSETS_DIR / "readme" / "kiviat-github.png"
README_KIVIAT_AREA_CHART = ASSETS_DIR / "readme" / "kiviat-areas-github.png"
README_GRAMMATICAL_CHART = ASSETS_DIR / "readme" / "grammatical-distribution-github.png"
KIVIAT_AREA_CHART = OUTPUT_DIR / "kiviat_areas.svg"
STATS_CACHE_MANIFEST = TEMP_DIR / "stats-cache.json"
METRIC_CACHE_VERSIONS = {
    "trigram_repetition": "2-lemmas-contextual-morphalou",
    "moving_trigram_repetition": "2-lemmas-contextual-morphalou",
}
README_STATS_START = "<!-- STATS:START -->"
README_STATS_END = "<!-- STATS:END -->"
MORPHALOU_BATCH_SIZE = 10_000
MORPHALOU_SCHEMA_VERSION = "2"
DEMONETTE_DIR = ASSETS_DIR / "demonette"
DEMONETTE_LEXEMES = DEMONETTE_DIR / "lexemes.csv"
DEMONETTE_INDEX = DEMONETTE_DIR / "demonette.sqlite3"
DEMONETTE_SCHEMA_VERSION = "2"
PHONETIC_MIN_SEQUENCE = 3
PHONETIC_MIN_RATIO = 0.6
REPETITION_PROXIMITY_WORDS = 300
STYLISTIC_EXACT_WEIGHT = 1.0
STYLISTIC_LEMMA_WEIGHT = 0.25
STYLISTIC_FAMILY_WEIGHT = 0.25
SPACY_FRENCH_MODEL = "fr_core_news_lg"
SPACY_RELATIVE_DEPENDENCIES = {"acl:relcl"}
SPACY_SUBORDINATE_DEPENDENCIES = {"acl", "advcl", "ccomp", "csubj", "xcomp"}
LEXICAL_WINDOW_SIZE = 300
MIN_COMPARISON_LEXICAL_WORDS = 200
COMPARISON_WINDOW_STEP_DIVISOR = 4

# Identifiants publics des mesures. Les rapports, la base SQLite et le site
# doivent référencer ces identifiants ; les noms Python ci-dessous ne servent
# qu'à accéder aux champs de TextStats.
METRICS = {
    "punctuation_per_300_words": "mesure_1",
    "punctuation_diversity": "mesure_2",
    "structural_diversity": "mesure_3",
    "structural_rhythm": "mesure_4",
    "sentence_start_diversity": "mesure_5",
    "burstiness": "mesure_6",
    "noun_verb_ratio": "mesure_7",
    "filtered_repetition_rate": "mesure_8",
    "stylistic_repetition_rate": "mesure_9",
    "family_repetition_rate": "mesure_10",
    "phonetic_repetition_rate": "mesure_11",
    "absolute_repetition_rate": "mesure_12",
    "function_word_ratio": "mesure_13",
    "trigram_repetition": "mesure_14",
    "moving_trigram_repetition": "mesure_15",
    "noun_ratio": "mesure_16",
    "verb_ratio": "mesure_17",
    "adjective_ratio": "mesure_18",
    "adverb_ratio": "mesure_19",
    "gzip_compression_ratio": "mesure_21",
    "relative_clause_ratio": "mesure_22",
    "nominal_sentence_ratio": "mesure_23",
    "active_voice_ratio": "mesure_24",
    "metaphorical_comme_ratio": "mesure_25",
    "average_syntactic_depth": "mesure_26",
    "form_lemma_ratio": "mesure_27",
    "hapax_ratio": "mesure_28",
    "word_count": "mesure_30",
    "sentence_count": "mesure_31",
    "paragraph_count": "mesure_32",
    "avg_word_length": "mesure_33",
    "avg_sentence_length": "mesure_34",
    "avg_sentence_word_count": "mesure_35",
    "median_sentence_length": "mesure_36",
    "sentence_length_p10": "mesure_37",
    "sentence_length_p90": "mesure_38",
    "paragraph_length_std_dev": "mesure_39",
    "document_char_count": "mesure_40",
    "unique_word_count": "mesure_42",
    "sentence_length_amplitude": "mesure_43",
    "sentence_length_std_dev": "mesure_44",
    "sentence_word_std_dev": "mesure_41",
    "type_token_ratio": "mesure_45",
    "moving_type_token_ratio": "mesure_46",
    "global_lemma_richness": "mesure_47",
    "lemma_richness": "mesure_48",
    "morphalou_coverage": "mesure_49",
    "lexical_word_count": "mesure_50",
    "unique_lemma_count": "mesure_51",
    "avg_paragraph_length": "mesure_52",
    "structural_repetition_rate": "mesure_53",
    "relative_clause_count": "mesure_54",
    "subordinate_clause_count": "mesure_55",
    "subordinate_clause_ratio": "mesure_56",
    "nominal_sentence_count": "mesure_57",
    "pos_common_noun_ratio": "mesure_58",
    "pos_proper_noun_ratio": "mesure_59",
    "pos_verb_ratio": "mesure_60",
    "pos_adjective_ratio": "mesure_61",
    "pos_adverb_ratio": "mesure_62",
    "flesch": "mesure_63",
    "present_participle_ratio": "mesure_64",
    "past_participle_ratio": "mesure_65",
    "simple_past_ratio": "mesure_66",
    "literary_subjunctive_ratio": "mesure_67",
    "negation_completeness_ratio": "mesure_68",
    "periphrastic_future_ratio": "mesure_69",
    "oral_familiarity_ratio": "mesure_70",
    "classicism_score": "mesure_71",
    "dialogue_ratio": "mesure_72",
    "negation_ratio": "mesure_73",
    "avg_modifiers_per_noun": "mesure_74",
    "heavily_modified_noun_ratio": "mesure_75",
    "lexical_rarity_score": "mesure_76",
    "adjective_chain_ratio": "mesure_77",
    "avg_adjective_chain_length": "mesure_78",
    "baroque_score": "mesure_79",
    "action_verb_ratio": "mesure_80",
    "temporal_connector_ratio": "mesure_81",
    "personal_subject_ratio": "mesure_82",
    "narrative_past_ratio": "mesure_83",
    "narrativity_score": "mesure_84",
    "emotion_word_ratio": "mesure_85",
    "affect_verb_ratio": "mesure_86",
    "exclamation_ratio": "mesure_87",
    "exclamative_construction_ratio": "mesure_88",
    "emotionality_score": "mesure_89",
    "logical_connector_ratio": "mesure_90",
    "abstract_noun_ratio": "mesure_91",
    "gnomic_present_ratio": "mesure_92",
    "discursivite_score": "mesure_93",
    "literary_tense_ratio": "mesure_94",
}

METRIC_FIELDS = tuple(METRICS)
METRIC_ID_BY_FIELD = dict(METRICS)
FIELD_BY_METRIC_ID = {identifier: field for field, identifier in METRICS.items() if identifier}


# Poids des scores composites. Les valeurs sont regroupées ici pour rendre
# les formules lisibles et faciles à modifier sans parcourir le fichier.
# Pour chaque axe, l'export compare d'abord chaque composante au maximum du
# corpus (valeur / maximum), puis calcule la somme « poids × composante
# normalisée ». Ainsi CLASSICISM_WEIGHTS correspond à :
# 0.30·literary_tense_ratio − 0.10·periphrastic_future_ratio
# − 0.20·oral_familiarity_ratio + 0.20·structural_diversity
# + 0.15·verb_ratio + 0.15·active_voice_ratio − 0.10·dialogue_ratio.
CLASSICISM_WEIGHTS = {
    "literary_tense_ratio": 0.30,
    "periphrastic_future_ratio": -0.10,
    "oral_familiarity_ratio": -0.20,
    "structural_diversity": 0.20,
    "verb_ratio": 0.15,
    "active_voice_ratio": 0.15,
    "dialogue_ratio": -0.10,
}

ORNATENESS_WEIGHTS = {
    "heavily_modified_noun_ratio": 0.30,
    "metaphorical_comme_ratio": 0.25,
    "adjective_chain_ratio": 0.25,
    "average_syntactic_depth": 0.10,
    "avg_sentence_length": 0.10,
}

NARRATIVITY_WEIGHTS = {
    "action_verb_ratio": 0.30,
    "temporal_connector_ratio": 0.20,
    "dialogue_ratio": 0.20,
    "active_voice_ratio": 0.15,
    "nominal_sentence_ratio": -0.10,
    "pos_adjective_ratio": -0.15,
}

EMOTIONALITY_WEIGHTS = {
    "affect_verb_ratio": 0.55,
    "exclamation_ratio": 0.45,
}

DISCURSIVITE_WEIGHTS = {
    "logical_connector_ratio": 0.50,
    "abstract_noun_ratio": 0.20,
    "gnomic_present_ratio": 0.30,
}

DEFAULT_UNIT = "paragraph"
TEXT_ENCODING = "utf-8"
