"""Configuration centrale des répertoires et fichiers du projet."""

from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parents[2]
README_FILE = PROJECT_ROOT / "README.md"

SCRIPT_DIR = PROJECT_ROOT / "script"
SOURCE_DIR = PROJECT_ROOT / "sources"
EPUB_DIR = PROJECT_ROOT / "_epub"
OUTPUT_DIR = PROJECT_ROOT / "_output"
WEB_DIR = PROJECT_ROOT / "web"
WEB_DATA_FILE = WEB_DIR / "data.json"
ASSETS_DIR = PROJECT_ROOT / "assets"
DICTIONARIES_DIR = ASSETS_DIR / "dictionnaires"
SITE_CONFIG_FILE = ASSETS_DIR / "site.yml"
README_TEXTS_FILE = ASSETS_DIR / "readme-texts.md"
CHART_PALETTE_FILE = ASSETS_DIR / "chart-palette.yml"
PUBLICATION_FILE = ASSETS_DIR / "publication.yml"
WIKIPEDIA_CACHE_FILE = ASSETS_DIR / "wikipedia-cache.json"
EPUB_DATABASE = ASSETS_DIR / "unshiter.sqlite3"
EPUB_ANALYSIS_WINDOW_SIZE = 20_000
EPUB_ANALYSIS_VERSION = "first-window-clean-body-v64-modal-generalization-optimized"
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
MORPHALOU_DIR = DICTIONARIES_DIR / "morphalou"
MORPHALOU_ARCHIVE = MORPHALOU_DIR / "Morphalou3.1_formatCSV_toutEnUn.zip"
MORPHALOU_CSV_MEMBER = "Morphalou3.1_formatCSV_toutEnUn/Morphalou3.1_CSV.csv"
MORPHALOU_INDEX = MORPHALOU_DIR / "morphalou.sqlite3"
FUNCTION_WORDS_FILE = DICTIONARIES_DIR / "function-words.txt"
COMPARISON_MARKERS_FILE = DICTIONARIES_DIR / "comparison-markers.txt"
FAMILIARITY_MARKERS_FILE = DICTIONARIES_DIR / "familiarity-markers.txt"
NEGATION_COMPLETE_MARKERS_FILE = DICTIONARIES_DIR / "negation-complete-markers.txt"
ABSTRACT_NOUN_SUFFIXES_FILE = DICTIONARIES_DIR / "abstract-noun-suffixes.txt"
CONCRETE_NOUN_EXCEPTIONS_FILE = DICTIONARIES_DIR / "concrete-noun-exceptions.txt"
DURATION_MARKERS_FILE = DICTIONARIES_DIR / "duration-markers.txt"
MODAL_VERBS_FILE = DICTIONARIES_DIR / "modal_verbs.txt"
LEXIQUE_DIR = DICTIONARIES_DIR / "lexique"
LEXIQUE_ARCHIVE = LEXIQUE_DIR / "Lexique383.tsv"
LEXIQUE_INDEX = LEXIQUE_DIR / "lexique.sqlite3"
STATIVE_VERBS_FILE = DICTIONARIES_DIR / "stative-verbs.txt"
TEMPORAL_CONNECTORS_FILE = DICTIONARIES_DIR / "temporal-connectors.txt"
LOGICAL_CONNECTORS_FILE = DICTIONARIES_DIR / "logical-connectors.txt"
AFFECT_VERBS_FILE = DICTIONARIES_DIR / "affect-verbs.txt"
FEEL_DIR = DICTIONARIES_DIR / "feel"
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
DEMONETTE_DIR = DICTIONARIES_DIR / "demonette"
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

def _metrics_from_notes() -> tuple[str, ...]:
    """Construit le registre depuis les titres de ``stats-notes.md``."""
    heading = re.compile(r"^# .+? \(([a-z][a-z0-9_]*)\)\s*$")
    metrics: list[str] = []
    malformed: list[str] = []
    for line_number, line in enumerate(STATS_NOTES_FILE.read_text(encoding="utf-8").splitlines(), 1):
        if not line.startswith("# "):
            continue
        match = heading.match(line)
        if not match:
            malformed.append(f"ligne {line_number}: {line}")
            continue
        field = match.group(1)
        if field.startswith("note_"):
            continue
        if field in metrics:
            raise ValueError(f"Fonction métrique dupliquée dans {STATS_NOTES_FILE}: {field}")
        metrics.append(field)
    if malformed:
        raise ValueError(
            f"Chaque note doit finir par '(nom_de_fonction)' dans {STATS_NOTES_FILE}:\n"
            + "\n".join(malformed)
        )
    if not metrics:
        raise ValueError(f"Aucune mesure définie dans {STATS_NOTES_FILE}")
    return tuple(metrics)


# Source de vérité unique : titre, identifiant et fonction vivent dans les notes.
METRICS = _metrics_from_notes()


# Les cinq axes de synthèse sont définis ici, au même endroit que les autres
# références de mesures, afin que les rapports n'en maintiennent pas une copie.
BIGFIVE_AXES = (
    ("Classique", "classicism_score"),
    ("Maximaliste", "baroque_score"),
    ("Narratif", "narrativity_score"),
    ("Émotionnel", "emotionality_score"),
    ("Discursif", "discursivite_score"),
)


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
    "heavily_modified_noun_ratio": 0.20,
    "metaphorical_comme_ratio": 0.15,
    "adjective_chain_ratio": 0.15,
    "avg_sentence_length": 0.10,
    "right_branching_depth": 0.20,
    "incise_density": 0.10,
    "coordination_accumulation_ratio": 0.10,
}

NARRATIVITY_WEIGHTS = {
    "action_verb_ratio": 0.25,
    "temporal_connector_ratio": 0.15,
    "dialogue_ratio": 0.15,
    "active_voice_ratio": 0.10,
    "tense_shift_rate": 0.20,
    "proper_noun_density": 0.10,
    "nominal_sentence_ratio": -0.08,
    "pos_adjective_ratio": -0.12,
}

EMOTIONALITY_WEIGHTS = {
    "affect_verb_ratio": 0.55,
    "exclamation_ratio": 0.45,
}

DISCURSIVITE_WEIGHTS = {
    "logical_connector_ratio": 0.55,
    "abstract_noun_ratio": 0.20,
    "gnomic_present_ratio": 0.25,
}

DEFAULT_UNIT = "paragraph"
TEXT_ENCODING = "utf-8"
