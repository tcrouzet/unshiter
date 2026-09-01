"""Configuration centrale des répertoires et fichiers du projet."""

from pathlib import Path
import os
import re

PROJECT_ROOT = Path(__file__).resolve().parents[2]
README_FILE = PROJECT_ROOT / "README.md"

SCRIPT_DIR = PROJECT_ROOT / "script"
CORPUS_DIR = PROJECT_ROOT / "corpus"
DEFAULT_CORPUS_ID = os.environ.get("UNSHITER_CORPUS", "bigcorpus")
ACTIVE_CORPUS_DIR = CORPUS_DIR / DEFAULT_CORPUS_ID
SOURCE_DIR = ACTIVE_CORPUS_DIR / "sources"
EPUB_DIR = ACTIVE_CORPUS_DIR / "_epub"
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
EMOTIONAL_INTERJECTIONS_FILE = DICTIONARIES_DIR / "emotional-interjections.txt"
EMOTIONS_FILE = DICTIONARIES_DIR / "emotions.txt"
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
    heading = re.compile(r"^#{1,6} .+? \(([a-z][a-z0-9_]*)\)\s*$")
    metrics: list[str] = []
    malformed: list[str] = []
    for line_number, line in enumerate(STATS_NOTES_FILE.read_text(encoding="utf-8").splitlines(), 1):
        if not re.match(r"^#{1,6}\s", line):
            continue
        match = heading.match(line)
        if not match:
            # Titre de section sans identifiant de fonction.
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

# Ces mesures sont des vues calculées à partir de comptes persistés. Elles
# restent dans METRICS et disposent d'une méthode Metrics, mais SQLite ne
# conserve pas une seconde copie de la même information.
DERIVED_METRICS = {
    "common_noun_ratio", "proper_noun_ratio", "nominal_sentence_ratio",
    "relative_clause_ratio", "subordinate_clause_ratio", "lexical_word_count",
    "question_mark_ratio",
}
PERSISTED_METRICS = tuple(field for field in METRICS if field not in DERIVED_METRICS)


def _metric_axes_from_notes(section_title: str) -> tuple[tuple[str, str], ...]:
    """Construit des axes depuis les métriques d'une section Markdown."""
    axes: list[tuple[str, str]] = []
    section_level: int | None = None
    expected_title = section_title.strip().casefold()
    heading = re.compile(r"^#{1,6}\s+(.+?) \(([a-z][a-z0-9_]*)\)\s*$")
    for line in STATS_NOTES_FILE.read_text(encoding="utf-8").splitlines():
        section = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if not section:
            continue
        level, title = len(section.group(1)), section.group(2).strip()
        if title.casefold() == expected_title:
            section_level = level
            continue
        if section_level is None:
            continue
        if level <= section_level:
            section_level = None
            continue
        match = heading.match(line)
        if not match:
            continue
        title, field = match.groups()
        if field not in METRICS:
            raise ValueError(f"Axe de la section {section_title!r} absent de METRICS: {field}")
        bold = re.findall(r"\*\*([^*]+)\*\*", title)
        label = bold[0].strip() if bold else title.replace("**", "").split("/", 1)[0].strip()
        axes.append((label, field))
    if not axes:
        raise ValueError(f"Section {section_title!r} vide ou absente dans {STATS_NOTES_FILE}")
    return tuple(axes)


BIGFIVE_AXES = _metric_axes_from_notes("BigFive")
RAW_METRICS = tuple(field for _label, field in _metric_axes_from_notes("Données brutes"))


# Poids des scores composites. Les valeurs sont regroupées ici pour rendre
# les formules lisibles et faciles à modifier sans parcourir le fichier.
# Pour chaque axe, l'export compare d'abord chaque composante au maximum du
# corpus (valeur / maximum), puis calcule la somme « poids × composante
# normalisée ». Ainsi CLASSICISM_WEIGHTS correspond à :
# 0.30·literary_subjunctive_ratio − 0.10·periphrastic_future_ratio
# − 0.20·oral_familiarity_ratio + 0.20·structural_diversity
# + 0.15·verb_ratio + 0.15·active_voice_ratio − 0.10·dialogue_ratio.
CLASSICISM_WEIGHTS = {
    "literary_subjunctive_ratio": 0.30,
    "periphrastic_future_ratio": -0.10,
    "oral_familiarity_ratio": -0.20,
    "structural_diversity": 0.20,
    "verb_ratio": 0.15,
    "active_voice_ratio": 0.15,
    "dialogue_ratio": -0.10,
    "punctuation_variety_score": 0.15,
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
    "adjective_ratio": -0.12,
}

EMOTIONALITY_WEIGHTS = {
    "emotion_sentence_ratio": 0.60,
    "emotion_intensification_ratio": 0.30,
    "emotional_category_entropy": 0.10
}

DISCURSIVITE_WEIGHTS = {
    "logical_connector_ratio": 0.55,
    "abstract_noun_ratio": 0.20,
    "gnomic_present_ratio": 0.25,
}

DEFAULT_UNIT = "paragraph"
TEXT_ENCODING = "utf-8"
