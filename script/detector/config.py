"""Configuration centrale des répertoires et fichiers du projet."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SCRIPT_DIR = PROJECT_ROOT / "script"
SOURCE_DIR = PROJECT_ROOT / "sources"
OUTPUT_DIR = PROJECT_ROOT / "_output"
ASSETS_DIR = PROJECT_ROOT / "assets"
TESTS_DIR = PROJECT_ROOT / "tests"
DOC_DIR = PROJECT_ROOT / "_doc"
TEMP_DIR = PROJECT_ROOT / "_temp"

DEFAULT_INPUT_FILE = SOURCE_DIR / "roman.md"
REPORT_FILENAME_SUFFIX = "_report"
STATS_FILENAME_SUFFIX = "_stats"
SOURCE_MARKDOWN_PATTERN = "*.md"
STANDARD_DEVIATION_REFERENCE_STEMS = ("lettre1", "reponse", "roman")
STANDARD_DEVIATION_MAXIMA = {
    "Burstiness": 2.0,
    "Ponctuation (signes/300 mots)": 300.0,
    "Lisibilité Flesch": 100.0,
    "Relatives et subordonnées": 200.0,
    "Profondeur syntaxique": 300.0,
}
MARKDOWN_EXTENSION = ".md"
JSON_EXTENSION = ".json"
STATS_COMPARISON_FILE = OUTPUT_DIR / "stats_comparison.md"
MORPHALOU_DIR = ASSETS_DIR / "morphalou"
MORPHALOU_ARCHIVE = MORPHALOU_DIR / "Morphalou3.1_formatCSV_toutEnUn.zip"
MORPHALOU_CSV_MEMBER = "Morphalou3.1_formatCSV_toutEnUn/Morphalou3.1_CSV.csv"
MORPHALOU_INDEX = MORPHALOU_DIR / "morphalou.sqlite3"
FUNCTION_WORDS_FILE = ASSETS_DIR / "function-words.txt"
STATS_NOTES_FILE = ASSETS_DIR / "stats-notes.md"
STRUCTURE_REPORT_SUFFIX = "_structure"
LEMMA_REPORT_SUFFIX = "_lemmes"
GRAMMATICAL_DISTRIBUTION_CHART = OUTPUT_DIR / "grammatical_distribution.svg"
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
AI_SCORE_FEATURES = {
    "structure_repetition": {"weight": 20, "low": 0.30, "high": 0.70, "inverse": False},
    "structure_diversity": {"weight": 15, "low": 0.30, "high": 0.80, "inverse": True},
    "sentence_variation": {"weight": 10, "low": 0.50, "high": 0.75, "inverse": True},
    "punctuation_density": {"weight": 15, "low": 36.0, "high": 54.0, "inverse": True},
    "punctuation_diversity": {"weight": 15, "low": 0.35, "high": 0.60, "inverse": True},
    "sentence_start_diversity": {"weight": 15, "low": 0.50, "high": 0.75, "inverse": True},
    "nominal_sentence_ratio": {"weight": 5, "low": 0.05, "high": 0.20, "inverse": True},
    "clause_density": {"weight": 5, "low": 0.50, "high": 1.50, "inverse": False},
}
LEXICAL_WINDOW_SIZE = 50
MIN_COMPARISON_LEXICAL_WORDS = 200
COMPARISON_WINDOW_STEP_DIVISOR = 4

DEFAULT_UNIT = "paragraph"
TEXT_ENCODING = "utf-8"
