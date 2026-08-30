"""Interface en ligne de commande des statistiques stylistiques."""

from dataclasses import fields, replace
from functools import lru_cache
from pathlib import Path
import argparse
import gzip
import hashlib
import html
import json
import math
import re
import shutil
import subprocess
import sqlite3

from .config import (
    JSON_EXTENSION,
    KIVIAT_CHART,
    KIVIAT_DETAIL_CHART,
    KIVIAT_AREA_CHART,
    LEMMA_REPORT_SUFFIX,
    GRAMMATICAL_DISTRIBUTION_CHART,
    MARKDOWN_EXTENSION,
    METRIC_CACHE_VERSIONS,
    OUTPUT_DIR,
    README_FILE,
    README_TEXTS_FILE,
    README_GRAMMATICAL_CHART,
    README_KIVIAT_AREA_CHART,
    README_KIVIAT_CHART,
    README_KIVIAT_DETAIL_CHART,
    README_STATS_END,
    README_STATS_START,
    SOURCE_DIR,
    EPUB_DIR,
    EPUB_DATABASE,
    SITE_CONFIG_FILE,
    SOURCE_MARKDOWN_PATTERN,
    STATS_CACHE_MANIFEST,
    STATS_NOTES_FILE,
    EPUB_ANALYSIS_WINDOW_SIZE,
    STATS_COMPARISON_FILE,
    WEB_DATA_FILE,
    BIGFIVE_AXES,
    STATS_FILENAME_SUFFIX,
    STRUCTURE_REPORT_SUFFIX,
    TEXT_ENCODING,
)
from .stats import TextStats, WORD_RE, _moving_trigram_repetition, _trigram_lemmas, _trigram_repetition, compute_stats, repetition_distribution, repetition_lemma_annotations, sentence_structure_signatures, split_sentences, split_structure_units, structure_is_eligible, tokenize, tokenize_repetitions
from .syntax_depth import analyze_syntax
from .metrics import cached_metric_values


FULL_DOCUMENT_FIELDS = {
    "word_count", "unique_word_count", "sentence_count", "paragraph_count",
    "lexical_word_count", "unique_lemma_count", "relative_clause_count",
    "subordinate_clause_count", "nominal_sentence_count", "dialogue_ratio", "oral_familiarity_ratio", "classicism_score", "baroque_score",
    "emotion_word_ratio", "affect_verb_ratio", "exclamation_ratio", "exclamative_construction_ratio", "emotionality_score",
    "logical_connector_ratio", "abstract_noun_ratio", "gnomic_present_ratio", "discursivite_score",
}


@lru_cache(maxsize=512)
def cached_compute_stats(text: str):
    return compute_stats(text)


def french_typography(text: str) -> str:
    """Applique l’espace insécable française avant le signe pour cent."""
    return text.replace(" %", "\u00a0%")


def readme_text(section: str) -> str:
    """Lit un texte éditable dans assets/readme-texts.md."""
    content = README_TEXTS_FILE.read_text(encoding=TEXT_ENCODING)
    match = re.search(rf"(?ms)^# {re.escape(section)}\s*\n\n(.*?)(?=^# |\Z)", content)
    if not match:
        raise RuntimeError(f"Section README absente : {section}")
    return match.group(1).strip()


def normalize_source_text(text: str) -> str:
    """Ramène les suites de plus de deux sauts de ligne à une ligne vide."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\n(?:[ \t]*\n){2,}", "\n\n", text)


def read_source(source: Path) -> str:
    return normalize_source_text(source.read_text(encoding=TEXT_ENCODING))


def is_human_source(source: Path) -> bool:
    # Les livres extraits dans _epub sont toujours des œuvres humaines. Pour
    # les Markdown autonomes, seul l'auteur déclaré dans le front matter
    # détermine le groupe IA ; le nom du fichier n'a aucune signification.
    if source.parent.resolve() != SOURCE_DIR.resolve():
        return True
    match = re.search(r"(?m)^author:\s*[\"']?([^\"'\n]+?)[\"']?\s*$", source.read_text(encoding=TEXT_ENCODING, errors="replace"))
    return not match or match.group(1).strip().casefold() != "ia"


def configured_comparison_sources() -> list[Path]:
    """Résout site.yml:default, puis ajoute tous les textes IA de sources."""
    configured = []
    in_default = False
    if SITE_CONFIG_FILE.exists():
        for line in SITE_CONFIG_FILE.read_text(encoding=TEXT_ENCODING).splitlines():
            if line.startswith("default:"):
                in_default = True
                continue
            if in_default and line and not line[0].isspace():
                break
            if in_default:
                match = re.match(r"^\s*-\s*[\"']?([^\"']+?)[\"']?\s*$", line)
                if match:
                    name = match.group(1)
                    candidates = []
                    if name.endswith(".epub"):
                        candidates.append(EPUB_DIR / (Path(name).stem + ".md"))
                    else:
                        candidates.extend((SOURCE_DIR / name, EPUB_DIR / name))
                    configured.extend(path for path in candidates if path.exists())
    # Les œuvres IA sont toujours ajoutées, même si elles ne figurent pas
    # dans la liste par défaut.
    configured.extend(path for path in sorted(SOURCE_DIR.glob(SOURCE_MARKDOWN_PATTERN)) if not is_human_source(path))
    unique = {path.resolve(): path.resolve() for path in configured}
    return sorted(unique.values(), key=lambda source: (is_human_source(source), display_name(source).casefold()))


def comparison_sources() -> list[Path]:
    """Œuvres de site.yml:default, puis IA, chaque groupe alphabétique."""
    return configured_comparison_sources()


def comparison_documents(sources: list[Path]) -> list[tuple[Path, str]]:
    """Conserve chaque œuvre comme un document distinct, comme le site web."""
    return [(source, read_source(source)) for source in sources]


def sqlite_analyses(sources: list[Path]) -> tuple[list[tuple[Path, TextStats]], int]:
    """Récupère les mesures déjà calculées dans SQLite, sans recalcul spaCy."""
    analyses = []
    with sqlite3.connect(EPUB_DATABASE) as connection:
        for source in sources:
            row = connection.execute("SELECT id FROM books WHERE path = ?", (str(source.resolve()),)).fetchone()
            if not row:
                raise RuntimeError(f"Source absente de SQLite : {source}")
            raw = cached_metric_values(connection, row[0])
            if not raw:
                raise RuntimeError(f"Analyse absente de SQLite : {source.name}")
            values = raw
            analyses.append((source, TextStats(**{field.name: values[field.name] for field in fields(TextStats) if field.name in values})))
    word_window = min(len(tokenize(read_source(source))) for source in sources) if sources else 0
    return analyses, word_window


def corpus_fingerprint(sources: list[Path]) -> str:
    """Empreinte du contenu source uniquement ; les mesures ont leurs versions."""
    paths = list(sources)
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: str(item)):
        digest.update(str(path.resolve()).encode(TEXT_ENCODING))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def comparison_output_paths(sources: list[Path]) -> list[Path]:
    outputs = [STATS_COMPARISON_FILE, KIVIAT_CHART, KIVIAT_DETAIL_CHART, KIVIAT_AREA_CHART, GRAMMATICAL_DISTRIBUTION_CHART]
    for source in sources:
        outputs.extend([
            OUTPUT_DIR / f"{source.stem}{STRUCTURE_REPORT_SUFFIX}{MARKDOWN_EXTENSION}",
            OUTPUT_DIR / f"{source.stem}{LEMMA_REPORT_SUFFIX}{MARKDOWN_EXTENSION}",
        ])
    return outputs


def read_comparison_cache(sources: list[Path], fingerprint: str):
    """Restitue les calculs, indépendamment des notes et du rendu Markdown."""
    if not STATS_CACHE_MANIFEST.exists():
        return None
    try:
        manifest = json.loads(STATS_CACHE_MANIFEST.read_text(encoding=TEXT_ENCODING))
        cached_fingerprint = manifest.get("corpus_fingerprint")
        if cached_fingerprint is not None and cached_fingerprint != fingerprint:
            return None
        if cached_fingerprint is None and any(source.stat().st_mtime_ns > STATS_CACHE_MANIFEST.stat().st_mtime_ns for source in sources):
            return None
        analyses = [
            (Path(item["source"]), TextStats.from_metric_dict(item["stats"]))
            for item in manifest["analyses"]
        ]
        versions = manifest.get("metric_versions", {})
        stale = {field for field, version in METRIC_CACHE_VERSIONS.items() if versions.get(field) != version}
        return analyses, int(manifest["window"]), stale
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def write_comparison_cache(fingerprint: str, analyses, window: int) -> None:
    STATS_CACHE_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "corpus_fingerprint": fingerprint,
        "metric_versions": METRIC_CACHE_VERSIONS,
        "window": window,
        "analyses": [
            {"source": str(source), "stats": stats.to_metric_dict()}
            for source, stats in analyses
        ],
    }
    STATS_CACHE_MANIFEST.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding=TEXT_ENCODING,
    )


def refresh_trigram_metrics(sources: list[Path], analyses, window: int):
    """Ne recalcule que les deux mesures de trigrammes devenues obsolètes."""
    texts = dict(comparison_documents(sources))
    refreshed = []
    for source, stats in analyses:
        global_values, local_values = [], []
        for fragment in source_windows(texts[source], window):
            words = tokenize(fragment)
            lemmas = _trigram_lemmas(words, tokenize_repetitions(fragment))
            global_values.append(_trigram_repetition(lemmas))
            local_values.append(_moving_trigram_repetition(lemmas))
        refreshed.append((source, replace(
            stats,
            trigram_repetition=sum(global_values) / len(global_values),
            moving_trigram_repetition=sum(local_values) / len(local_values),
        )))
    return refreshed


def source_windows(text: str, size: int, minimum_final_ratio: float = 0.7) -> list[str]:
    """Fenêtres non chevauchantes bornées par les paragraphes.

    Une dernière fenêtre trop courte est ignorée, sauf lorsqu'elle constitue
    l'unique fenêtre disponible pour le texte.
    """
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        return [text]
    windows: list[str] = []
    current: list[str] = []
    current_words = 0
    for paragraph in paragraphs:
        current.append(paragraph)
        current_words += len(tokenize(paragraph))
        if current_words >= size:
            windows.append("\n\n".join(current))
            current, current_words = [], 0
    if current:
        fragment = "\n\n".join(current)
        if not windows or current_words >= size * minimum_final_ratio:
            windows.append(fragment)
    return windows or [text]


def byte_windows(text: str, size: int) -> list[bytes]:
    """Blocs UTF-8 non chevauchants et strictement comparables pour gzip."""
    data = text.encode(TEXT_ENCODING)
    if len(data) <= size:
        return [data]
    return [data[start:start + size] for start in range(0, len(data) - size + 1, size)]


def gzip_window_ratio(text: str, size: int) -> float:
    samples = byte_windows(text, size)
    ratios = [len(gzip.compress(sample, mtime=0)) / len(sample) for sample in samples if sample]
    return sum(ratios) / len(ratios) if ratios else 0


def comparable_stats(text: str, full_stats, window: int, gzip_window: int):
    """Moyenne les mesures dérivées sur des fenêtres comparables."""
    samples = [cached_compute_stats(fragment) for fragment in source_windows(text, window)]
    base = full_stats or samples[0]
    updates = {}
    for field in fields(base):
        if field.name in FULL_DOCUMENT_FIELDS:
            continue
        values = [getattr(sample, field.name) for sample in samples]
        numeric = [value for value in values if value is not None]
        updates[field.name] = sum(numeric) / len(numeric) if numeric else None
    words = tokenize(text)
    full_syntax = analyze_syntax(text)
    updates.update({
        "word_count": len(words),
        "unique_word_count": getattr(base, "unique_lemma_count", 0) / len(words) if words else 0,
        "sentence_count": len(split_sentences(text)),
        "paragraph_count": len([part for part in re.split(r"\n\s*\n", text) if part.strip()]),
        "gzip_compression_ratio": gzip_window_ratio(text, gzip_window),
        "active_voice_ratio": full_syntax["active_voice_ratio"] if full_syntax else None,
        "metaphorical_comme_ratio": full_syntax["metaphorical_comme_ratio"] if full_syntax else None,
        "simple_past_ratio": full_syntax["simple_past"] / full_syntax["finite_verbs"] if full_syntax and full_syntax["finite_verbs"] else 0,
        "literary_subjunctive_ratio": full_syntax["literary_subjunctive"] / full_syntax["finite_verbs"] if full_syntax and full_syntax["finite_verbs"] else 0,
        "negation_completeness_ratio": full_syntax["negation_completeness_ratio"] if full_syntax else None,
        "periphrastic_future_ratio": full_syntax["periphrastic_future_ratio"] if full_syntax else None,
        "dialogue_ratio": full_syntax["dialogue_ratio"] if full_syntax else 0,
        "oral_familiarity_ratio": full_stats.oral_familiarity_ratio if full_stats else 0,
        "classicism_score": full_stats.classicism_score if full_stats else 0,
    })
    return replace(base, **updates)


def comparable_analyses(sources: list[Path], analyses: list[tuple[Path, object]] | None = None):
    documents = comparison_documents(sources)
    texts = [text for _, text in documents]
    window = min(len(tokenize(text)) for text in texts)
    gzip_window = min(len(text.encode(TEXT_ENCODING)) for text in texts)
    full = analyses or [(source, None) for source, _ in documents]
    compared = [
        (source, comparable_stats(text, stats, window, gzip_window))
        for (source, stats), text in zip(full, texts)
    ]
    # Les axes sont classés sur toutes les fenêtres présentes en SQLite, et
    # non sur la seule sélection affichée. Le rang percentile donne une
    # échelle commune sans inventer de maximum propre à chaque mesure.
    corpus_values = {}
    try:
        with sqlite3.connect(EPUB_DATABASE) as db:
            rows = []
            for (book_id,) in db.execute("SELECT id FROM books"):
                rows.append((json.dumps(cached_metric_values(db, book_id)),))
        for field in ("classicism_score", "baroque_score", "emotionality_score", "narrativity_score", "discursivite_score"):
            identifier = field
            values = []
            for (raw,) in rows:
                data = json.loads(raw)
                value = data.get(identifier)
                if isinstance(value, (int, float)) and math.isfinite(value):
                    values.append(float(value))
            corpus_values[field] = values
    except (OSError, sqlite3.Error, json.JSONDecodeError):
        corpus_values = {}
    for field in ("classicism_score", "baroque_score", "emotionality_score", "narrativity_score", "discursivite_score"):
        values = corpus_values.get(field) or [float(getattr(item, field, 0) or 0) for _, item in compared]
        ordered = sorted(values)
        def rank(value):
            if len(ordered) <= 1:
                return 0.0
            lower = sum(v < value for v in ordered)
            equal = sum(v == value for v in ordered)
            return (lower + (equal - 1) / 2) / (len(ordered) - 1)
        compared = [(source, replace(item, **{field: rank(float(getattr(item, field, 0) or 0))})) for source, item in compared]
    return compared, window


def output_paths(source: Path) -> tuple[Path, Path]:
    stem = f"{source.stem}{STATS_FILENAME_SUFFIX}"
    return OUTPUT_DIR / f"{stem}{MARKDOWN_EXTENSION}", OUTPUT_DIR / f"{stem}{JSON_EXTENSION}"


def statistic_rows(stats, comparison: dict | None = None) -> list[tuple[str, object]]:
    percent = lambda value: f"{value * 100:.0f} %"
    rows = [
        ("Mots", stats.word_count), ("Phrases", stats.sentence_count), ("Paragraphes", stats.paragraph_count),
        ("Longueur moyenne des mots (caractères)", f"{stats.avg_word_length:.1f}"),
        ("Longueur moyenne des phrases (caractères)", f"{stats.avg_sentence_length:.1f}"),
        ("Longueur moyenne des phrases (mots)", f"{stats.avg_sentence_word_count:.1f}"),
        ("Longueur médiane des phrases (caractères)", f"{stats.median_sentence_length:.1f}"),
        ("Longueur P10 des phrases (caractères)", f"{stats.sentence_length_p10:.1f}"),
        ("Longueur P90 des phrases (caractères)", f"{stats.sentence_length_p90:.1f}"),
        ("Burstiness[^2]", f"{stats.burstiness:.2f}"),
        ("Diversité stylistique", f"{(1 - stats.stylistic_repetition_rate) * 100:.1f} %"),
        ("Répétitions lexicales[^10]", f"{(comparison['filtered'] if comparison else stats.filtered_repetition_rate) * 100:.0f} %"),
        ("Répétitions familiales[^11]", f"{(comparison['family'] if comparison else stats.family_repetition_rate) * 100:.0f} %"),
        ("Répétitions sonores[^12]", f"{(comparison['phonetic'] if comparison else stats.phonetic_repetition_rate) * 100:.0f} %"),
        ("Répétitions non filtrées", f"{(comparison['absolute'] if comparison else stats.absolute_repetition_rate) * 100:.0f} %"),
        ("Répétition globale des trigrammes", f"{stats.trigram_repetition * 100:.1f} %"),
        ("Répétition locale des trigrammes", f"{stats.moving_trigram_repetition * 100:.1f} %"),
        ("Mots-outils[^13]", percent(stats.function_word_ratio)),
        ("Noms", f"{stats.noun_ratio * 100:.0f} %"),
        ("Verbes", f"{stats.verb_ratio * 100:.0f} %"),
        ("Adjectifs", f"{stats.adjective_ratio * 100:.0f} %"),
        ("Adverbes", f"{stats.adverb_ratio * 100:.0f} %"),
        ("Participes présents", f"{stats.present_participle_ratio * 100:.0f} %" if stats.present_participle_ratio is not None else "indisponible"),
        ("Participes passés", f"{stats.past_participle_ratio * 100:.0f} %" if stats.past_participle_ratio is not None else "indisponible"),
        ("Passé simple[^66]", f"{stats.simple_past_ratio * 100:.1f} %"),
        ("Subjonctif littéraire[^67]", f"{stats.literary_subjunctive_ratio * 100:.1f} %"),
        ("Négations complètes[^68]", f"{stats.negation_completeness_ratio * 100:.1f} %" if stats.negation_completeness_ratio is not None else "—"),
        ("Futur périphrastique[^69]", f"{stats.periphrastic_future_ratio * 100:.1f} %" if stats.periphrastic_future_ratio is not None else "—"),
        ("Familiarité orale[^70]", f"{stats.oral_familiarity_ratio:.1f} %"),
        ("Classique / Contemporain[^71]", f"{stats.classicism_score * 100:.1f} %"),
        ("Dialogue[^72]", f"{stats.dialogue_ratio * 100:.1f} %"),
        ("Négativité / Positivité[^73]", f"{stats.negation_ratio * 100:.1f} %"),
        ("Modificateurs par nom[^74]", f"{stats.avg_modifiers_per_noun:.2f}"),
        ("Noms fortement modifiés[^75]", f"{stats.heavily_modified_noun_ratio * 100:.1f} %"),
        ("Rareté lexicale[^76]", f"{stats.lexical_rarity_score:.2f}"),
        ("Chaînes adjectivales[^77]", f"{stats.adjective_chain_ratio * 100:.1f} %"),
        ("Longueur des chaînes adjectivales[^78]", f"{stats.avg_adjective_chain_length:.2f}"),
        ("Maximaliste / Minimaliste[^79]", f"{stats.baroque_score * 100:.1f} %"),
        ("Verbes d’action[^80]", f"{stats.action_verb_ratio * 100:.1f} %"),
        ("Connecteurs temporels[^81]", f"{stats.temporal_connector_ratio:.1f} %"),
        ("Sujets personnels[^82]", f"{stats.personal_subject_ratio * 100:.1f} %"),
        ("Passé narratif[^83]", f"{stats.narrative_past_ratio * 100:.1f} %" if stats.narrative_past_ratio is not None else "—"),
        ("Narratif / Descriptif[^84]", f"{stats.narrativity_score * 100:.1f} %"),
        ("Mots émotionnels[^85]", f"{stats.emotion_word_ratio * 100:.1f} %"),
        ("Verbes de réaction affective[^86]", f"{stats.affect_verb_ratio * 100:.1f} %"),
        ("Exclamations[^87]", f"{stats.exclamation_ratio * 100:.1f} %"),
        ("Constructions exclamatives[^88]", f"{stats.exclamative_construction_ratio * 100:.1f} %"),
        ("Émotionnel / Neutre[^89]", f"{stats.emotionality_score * 100:.1f} %"),
        ("Connecteurs logiques[^90]", f"{stats.logical_connector_ratio:.1f} %"),
        ("Noms abstraits[^91]", f"{stats.abstract_noun_ratio * 100:.1f} %"),
        ("Présent gnomique[^92]", f"{stats.gnomic_present_ratio * 100:.1f} %" if stats.gnomic_present_ratio is not None else "—"),
        ("Discursif / Immersif[^93]", f"{stats.discursivite_score * 100:.1f} %"),
        ("Ratio noms/verbes", f"{stats.noun_verb_ratio:.2f}"),
        ("Diversité des structures[^4]", f"{stats.structural_diversity * 100:.0f} %"),
        ("Diversité de longueurs de phrase (mots)", f"{stats.sentence_word_std_dev:.1f}"),
        ("Rythme des structures[^14]", f"{stats.structural_rhythm * 100:.0f} %"),
        ("Compression gzip[^5]", f"{stats.gzip_compression_ratio * 100:.0f} %"),
        ("Relatives[^6]", f"{stats.relative_clause_ratio * 100:.0f} %" if stats.relative_clause_ratio is not None else "indisponible"),
        ("Densité de ponctuations", f"{stats.punctuation_per_300_words:.1f} %"),
        ("Diversité de ponctuation", f"{stats.punctuation_diversity * 100:.0f} %"),
        ("Phrases nominales[^15]", f"{stats.nominal_sentence_ratio * 100:.0f} %" if stats.nominal_sentence_ratio is not None else "indisponible"),
        ("Voix active", f"{stats.active_voice_ratio * 100:.0f} %" if stats.active_voice_ratio is not None else "indisponible"),
        ("Comparaisons métaphoriques", f"{stats.metaphorical_comme_ratio * 100:.1f} %" if stats.metaphorical_comme_ratio is not None else "indisponible"),
        ("Écart-type des paragraphes (mots)", f"{stats.paragraph_length_std_dev:.1f}"),
        ("Profondeur syntaxique[^18]", f"{stats.average_syntactic_depth:.1f}" if stats.average_syntactic_depth is not None else "indisponible"),
    ]
    rows += [
        ("Formes par lemme", f"{stats.form_lemma_ratio:.2f}"),
        ("Diversité des débuts de phrase", f"{stats.sentence_start_diversity * 100:.0f} %"),
        ("Mots employés une seule fois", f"{stats.hapax_ratio * 100:.0f} %"),
        ("Fenêtres analysées", comparison["count"] if comparison else 1),
        ("Longueur moyenne des paragraphes (mots)", f"{stats.avg_paragraph_length:.1f}"),
    ]
    return rows


IMPORTANT_LABELS = (
    "Densité de ponctuations",
    "Diversité de ponctuation",
    "Diversité des structures",
    "Rythme des structures",
    "Profondeur syntaxique",
    "Diversité des débuts de phrase",
    "Burstiness",
    "Ratio noms/verbes",
    "Répétitions lexicales",
)

TECHNICAL_LABELS = {
    "Mots",
    "Phrases",
    "Paragraphes",
    "Longueur moyenne des mots (caractères)",
    "Longueur moyenne des phrases (caractères)",
    "Longueur moyenne des phrases (mots)",
    "Longueur médiane des phrases (caractères)",
    "Longueur P10 des phrases (caractères)",
    "Longueur P90 des phrases (caractères)",
    "Écart-type des paragraphes (mots)",
    "Longueur moyenne des paragraphes (mots)",
    "Fenêtres analysées",
}

# Dimensions utilisées par l'attribution Burrows. Elles sont volontairement
# limitées aux mesures stylistiques comparables, sans volumes ni longueurs
# absolues qui rapprocheraient mécaniquement les textes de même taille.
NEAREST_NEIGHBOR_FIELDS = (
    "punctuation_per_300_words", "punctuation_diversity", "structural_diversity", "structural_rhythm",
    "sentence_start_diversity", "burstiness", "noun_verb_ratio", "filtered_repetition_rate",
    "stylistic_repetition_rate", "family_repetition_rate", "phonetic_repetition_rate", "absolute_repetition_rate",
    "function_word_ratio", "trigram_repetition", "moving_trigram_repetition", "noun_ratio", "verb_ratio",
    "adjective_ratio", "adverb_ratio", "present_participle_ratio", "past_participle_ratio", "gzip_compression_ratio", "relative_clause_ratio",
    "nominal_sentence_ratio", "active_voice_ratio", "metaphorical_comme_ratio", "average_syntactic_depth",
    "form_lemma_ratio", "hapax_ratio", "sentence_word_std_dev", "sentence_length_amplitude", "sentence_length_std_dev",
    "simple_past_ratio", "literary_subjunctive_ratio", "negation_completeness_ratio",
    "periphrastic_future_ratio", "oral_familiarity_ratio", "classicism_score",
    "emotion_word_ratio", "affect_verb_ratio", "exclamation_ratio", "exclamative_construction_ratio", "emotionality_score",
    "dialogue_ratio", "negation_ratio", "narrative_past_ratio", "narrativity_score",
    "logical_connector_ratio", "abstract_noun_ratio", "gnomic_present_ratio", "discursivite_score",
)


def nearest_neighbor_markdown() -> list[str]:
    """Rend l'attribution Burrows des textes IA vers les œuvres humaines."""
    if not EPUB_DATABASE.exists():
        return []
    rows = []
    # Le site exporte la représentation canonique des œuvres et des mesures.
    # Le rapport réutilise ce JSON pour éviter une seconde définition du corpus.
    if WEB_DATA_FILE.exists():
        try:
            payload = json.loads(WEB_DATA_FILE.read_text(encoding=TEXT_ENCODING))
            for book in payload.get("books", []):
                analysis = (book.get("analyses") or [{}])[0]
                rows.append({"title": book.get("title") or Path(book.get("filename", "")).stem,
                             "author": book.get("author") or "Auteur inconnu",
                             "values": analysis.get("stats", {})})
        except (OSError, json.JSONDecodeError, TypeError):
            rows = []
    if not rows:
        with sqlite3.connect(EPUB_DATABASE) as connection:
            for book_id, title, author, path in connection.execute("SELECT id, title, author, path FROM books ORDER BY title"):
                values = cached_metric_values(connection, book_id)
                if not values:
                    continue
                rows.append({"title": title or Path(path).stem, "author": author or "Auteur inconnu", "values": values})
    if len(rows) < 3:
        return []
    ids = list(NEAREST_NEIGHBOR_FIELDS)
    usable = [[float(book["values"][identifier]) if book["values"].get(identifier) is not None else None for identifier in ids] for book in rows]
    means, deviations = [], []
    for index in range(len(ids)):
        values = [row[index] for row in usable if row[index] is not None]
        mean = sum(values) / len(values) if values else 0.0
        deviation = math.sqrt(sum((value - mean) ** 2 for value in values) / len(values)) if values else 0.0
        means.append(mean); deviations.append(deviation)
    def distance(left, right):
        parts = [abs((left[index] - means[index]) / deviations[index] - (right[index] - means[index]) / deviations[index]) for index in range(len(ids)) if left[index] is not None and right[index] is not None and deviations[index] > 0]
        return sum(parts) / len(parts) if parts else None
    ia = [index for index, book in enumerate(rows) if book["author"].strip().casefold() == "ia"]
    if not ia:
        return []
    human = [index for index, book in enumerate(rows) if book["author"].strip().casefold() != "ia"]
    lines = ["## Attribution au plus proche voisin", "", f"Distance de Burrows : moyenne des écarts absolus entre z-scores sur {len(NEAREST_NEIGHBOR_FIELDS)} mesures stylistiques. Les textes IA sont comparés aux œuvres humaines du corpus complet ; une distance faible signifie seulement une proximité statistique, pas une preuve d’auteur ou de modèle.", "", "| Texte IA | Voisin humain | Δ |", "|---|---|---:|"]
    for ia_index in ia:
        candidates = [(distance(usable[ia_index], usable[index]), index) for index in human]
        candidates = sorted((value, index) for value, index in candidates if value is not None)[:5]
        for rank, (value, index) in enumerate(candidates):
            source = rows[ia_index] if rank == 0 else {"title": "", "author": ""}
            ia_label = f"{rows[ia_index]['title']} — {rows[ia_index]['author']}" if rank == 0 else ""
            human_label = f"{rows[index]['title']} — {rows[index]['author']}"
            lines.append(f"| {ia_label} | {human_label} | {value:.2f} |")
    return lines

def split_rows(rows: list[tuple[str, object]]) -> tuple[list[tuple[str, object]], list[tuple[str, object]]]:
    rows = [(re.sub(r"\[\^\d+\]$", "", label), value) for label, value in rows]
    row_map = dict(rows)
    important = [(label, row_map[label]) for label in IMPORTANT_LABELS if label in row_map]
    details = [row for row in rows if row[0] not in IMPORTANT_LABELS]
    details = (
        [row for row in details if row[0] not in TECHNICAL_LABELS]
        + [row for row in details if row[0] in TECHNICAL_LABELS]
    )
    return important, details


def markdown_sections(path: Path) -> dict[str, str]:
    """Lit un fichier Markdown organisé en sections de premier niveau."""
    if not path.exists():
        return {}
    sections: dict[str, list[str]] = {}
    current_title = None
    window_label = f"{EPUB_ANALYSIS_WINDOW_SIZE / 1000:g}"
    for line in path.read_text(encoding=TEXT_ENCODING).replace("{windows}", window_label).splitlines():
        if line.startswith("### "):
            current_title = line[4:].strip()
            sections[current_title] = []
        elif line.startswith("#"):
            current_title = None
        elif current_title is not None:
            sections[current_title].append(line)
    return {title: "\n".join(content).strip() for title, content in sections.items()}


def note_sections() -> dict[str, str]:
    return markdown_sections(STATS_NOTES_FILE)




def _note_heading_matches(heading: str, label: str) -> bool:
    """Compare un libellé de tableau avec l'un des titres de la note."""
    if label == "Dispersion":
        return heading.startswith("Dispersion")
    clean_heading = re.sub(r"\s+\([a-z][a-z0-9_]*\)\s*$", "", heading)
    clean_heading = clean_heading.replace("**", "")
    alternatives = [part.strip() for part in clean_heading.split("/")]
    return label.strip() in alternatives


def note_section_for(label: str) -> str | None:
    for heading, content in note_sections().items():
        if _note_heading_matches(heading, label):
            return content
    return None


def number_notes(rows: list[tuple[str, object]], prefix_titles: list[str] | None = None) -> tuple[list[tuple[str, object]], list[str]]:
    titles = (prefix_titles or []) + [label for label, _ in rows if note_section_for(label) is not None]
    numbers = {title: index for index, title in enumerate(titles, 1)}
    return [
        (f"{label}[^{numbers[label]}]" if label in numbers else label, value)
        for label, value in rows
    ], titles


def numeric_value(value: object) -> float | None:
    match = re.search(r"-?\d+(?:[.,]\d+)?", str(value).replace(" ", "").replace("\u00a0", ""))
    return float(match.group(0).replace(",", ".")) if match else None


def statistic_numeric_values(stats, comparison: dict | None = None) -> dict[str, float]:
    """Valeurs non arrondies, dans les unités affichées, pour calculer σ."""
    percent = lambda value: value * 100
    return {
        "Burstiness": stats.burstiness,
        "Diversité stylistique": percent(1 - stats.stylistic_repetition_rate),
        "Répétitions lexicales": percent(comparison["filtered"] if comparison else stats.filtered_repetition_rate),
        "Répétitions familiales": percent(comparison["family"] if comparison else stats.family_repetition_rate),
        "Répétitions sonores": percent(comparison["phonetic"] if comparison else stats.phonetic_repetition_rate),
        "Répétitions non filtrées": percent(comparison["absolute"] if comparison else stats.absolute_repetition_rate),
        "Répétition globale des trigrammes": percent(stats.trigram_repetition),
        "Répétition locale des trigrammes": percent(stats.moving_trigram_repetition),
        "Mots-outils": percent(stats.function_word_ratio),
        "Noms": percent(stats.noun_ratio), "Verbes": percent(stats.verb_ratio),
        "Adjectifs": percent(stats.adjective_ratio), "Adverbes": percent(stats.adverb_ratio),
        "Ratio noms/verbes": stats.noun_verb_ratio,
        "Diversité des structures": percent(stats.structural_diversity),
        "Diversité de longueurs de phrase (mots)": stats.sentence_word_std_dev,
        "Rythme des structures": percent(stats.structural_rhythm),
        "Compression gzip": percent(stats.gzip_compression_ratio),
        "Relatives": percent(stats.relative_clause_ratio),
        "Densité de ponctuations": stats.punctuation_per_300_words,
        "Diversité de ponctuation": percent(stats.punctuation_diversity),
        "Phrases nominales": percent(stats.nominal_sentence_ratio or 0),
        "Voix active": percent(stats.active_voice_ratio or 0),
        "Comparaisons métaphoriques": percent(stats.metaphorical_comme_ratio or 0),
        "Profondeur syntaxique": stats.average_syntactic_depth,
        "Formes par lemme": stats.form_lemma_ratio,
        "Diversité des débuts de phrase": percent(stats.sentence_start_diversity),
        "Mots employés une seule fois": percent(stats.hapax_ratio),
    }


def coefficient_dispersions(rows_by_file: list[list[tuple[str, object]]], numeric_maps: list[dict[str, float]] | None = None) -> dict[str, str]:
    """Écart-type robuste entre auteurs rapporté à leur moyenne."""
    def percentile(sorted_values: list[float], fraction: float) -> float:
        position = (len(sorted_values) - 1) * fraction
        lower, upper = math.floor(position), math.ceil(position)
        if lower == upper:
            return sorted_values[lower]
        return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * (position - lower)

    def without_outliers(values: list[float]) -> list[float]:
        if len(values) < 4:
            return values
        ordered = sorted(values)
        first_quartile, third_quartile = percentile(ordered, .25), percentile(ordered, .75)
        interval = third_quartile - first_quartile
        retained = [value for value in values if first_quartile - 1.5 * interval <= value <= third_quartile + 1.5 * interval]
        return retained if len(retained) >= 3 else values

    row_maps = [dict(rows) for rows in rows_by_file]
    result = {}
    for label, _ in rows_by_file[0]:
        plain_label = re.sub(r"\[\^\d+\]$", "", label)
        if plain_label in TECHNICAL_LABELS:
            result[plain_label] = "—"
            continue
        values = ([numeric.get(plain_label) for numeric in numeric_maps] if numeric_maps is not None
                  else [numeric_value(rows.get(label)) for rows in row_maps])
        values = [value for value in values if value is not None]
        values = without_outliers(values)
        mean = sum(values) / len(values) if values else 0
        if not mean:
            result[plain_label] = "—"
            continue
        standard_deviation = math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))
        result[plain_label] = f"{standard_deviation / abs(mean) * 100:.1f} %"
    return result


def markdown_table(headers: list[str], rows_by_file: list[list[tuple[str, object]]], dispersions: dict[str, str] | None = None) -> list[str]:
    displayed_headers = headers + (["Dispersion (σ)[^1]"] if dispersions is not None else [])
    lines = ["| Mesure | " + " | ".join(displayed_headers) + " |", "|---|" + "---:|" * len(displayed_headers)]
    for index, (label, _) in enumerate(rows_by_file[0]):
        values = [str(rows[index][1]) for rows in rows_by_file]
        plain_label = re.sub(r"\[\^\d+\]$", "", label)
        dispersion = [dispersions.get(plain_label, "—")] if dispersions is not None else []
        lines.append(f"| {label} | " + " | ".join(values + dispersion) + " |")
    return lines


def grammatical_distribution_table(title: str, stats) -> list[str]:
    values = [
        ("Noms communs", stats.pos_common_noun_ratio),
        ("Noms propres", stats.pos_proper_noun_ratio),
        ("Verbes", stats.verb_ratio),
        ("Adjectifs", stats.adjective_ratio),
        ("Adverbes", stats.adverb_ratio),
    ]
    lines = [f"### {title}", "", "| Catégorie | Part |", "|---|---:|"]
    if any(value is None for _, value in values):
        lines.append("| Analyse spaCy | indisponible |")
    else:
        lines.extend(f"| {label} | {value * 100:.1f} % |" for label, value in values)
    return lines


def grammatical_distribution_chart(analyses: list[tuple[Path, object]]) -> str:
    """SVG de camemberts, au maximum trois par ligne, avec légende commune."""
    categories = [
        ("Noms communs", "pos_common_noun_ratio", "#3d70a3"),
        ("Noms propres", "pos_proper_noun_ratio", "#75a843"),
        ("Adverbes", "adverb_ratio", "#efb349"),
        ("Verbes", "verb_ratio", "#ca4038"),
        ("Adjectifs", "adjective_ratio", "#835692"),
    ]
    columns = min(3, max(1, len(analyses)))
    rows = math.ceil(len(analyses) / columns)
    width, height = max(360 * columns, 950), rows * 340 + 90
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:#222}.title{font-size:20px;font-weight:700}.value{font-size:14px;font-weight:700;fill:white;paint-order:stroke;stroke:#333;stroke-width:3px}.legend{font-size:14px}</style>',
    ]
    for chart_index, (source, stats) in enumerate(analyses):
        column, row = chart_index % columns, chart_index // columns
        center_x, center_y, radius = 180 + column * 360, 170 + row * 340, 120
        parts.append(f'<text class="title" x="{center_x}" y="{center_y - 142}" text-anchor="middle">{html.escape(display_name(source))}</text>')
        values = [(label, getattr(stats, attribute), color) for label, attribute, color in categories]
        if any(value is None for _, value, _ in values):
            parts.append(f'<text x="{center_x}" y="{center_y}" text-anchor="middle">Analyse spaCy indisponible</text>')
            continue
        angle = -math.pi / 2
        for _, value, color in values:
            end = angle + value * 2 * math.pi
            x1, y1 = center_x + radius * math.cos(angle), center_y + radius * math.sin(angle)
            x2, y2 = center_x + radius * math.cos(end), center_y + radius * math.sin(end)
            large = 1 if end - angle > math.pi else 0
            parts.append(f'<path d="M {center_x} {center_y} L {x1:.2f} {y1:.2f} A {radius} {radius} 0 {large} 1 {x2:.2f} {y2:.2f} Z" fill="{color}"/>')
            if value >= .04:
                middle = (angle + end) / 2
                label_x = center_x + radius * .65 * math.cos(middle)
                label_y = center_y + radius * .65 * math.sin(middle)
                parts.append(f'<text class="value" x="{label_x:.2f}" y="{label_y:.2f}" text-anchor="middle">{value * 100:.0f} %</text>')
            angle = end
    item_widths = [39 + len(label) * 7 for label, _, _ in categories]
    legend_gap = 18
    legend_width = sum(item_widths) + legend_gap * (len(categories) - 1)
    legend_x = (width - legend_width) / 2
    legend_y = height - 35
    for index, (label, _, color) in enumerate(categories):
        x = legend_x
        parts.append(f'<rect x="{x:.1f}" y="{legend_y - 13}" width="16" height="16" rx="2" fill="{color}"/>')
        parts.append(f'<text class="legend" x="{x + 23:.1f}" y="{legend_y}">{html.escape(label)}</text>')
        legend_x += item_widths[index] + legend_gap
    parts.append("</svg>")
    return french_typography("\n".join(parts))


KIVIAT_COLORS = ["#4a2c20", "#d13c36", "#3478b8", "#57a052", "#8b55a2", "#e19a2d", "#2b9b9b"]


def kiviat_profiles(analyses: list[tuple[Path, object]]):
    """Dimensions et rayons du radar, partagés par tous ses graphiques."""
    candidates = [
        ("Densité de ponctuations", lambda s: s.punctuation_per_300_words, False, False),
        ("Diversité de ponctuation", lambda s: s.punctuation_diversity, False, True),
        ("Diversité des structures", lambda s: s.structural_diversity, False, True),
        ("Rythme des structures", lambda s: s.structural_rhythm, False, True),
        ("Profondeur syntaxique", lambda s: s.average_syntactic_depth, False, False),
        ("Diversité des débuts de phrase", lambda s: s.sentence_start_diversity, False, True),
        ("Burstiness", lambda s: s.burstiness, False, False),
        ("Ratio noms/verbes", lambda s: s.noun_verb_ratio, False, False),
        ("Répétitions lexicales", lambda s: s.filtered_repetition_rate, True, True),
    ]
    dimensions = []
    for label, getter, inverse, is_percent in candidates:
        values = [getter(stats) for _, stats in analyses]
        if any(value is None for value in values):
            continue
        mean = sum(values) / len(values)
        if not mean:
            continue
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        std_dev = math.sqrt(variance)
        dimensions.append((label, values, mean, std_dev, inverse, is_percent))
    profiles = []
    for series_index in range(len(analyses)):
        radii = []
        for _, values, mean, std_dev, inverse, _ in dimensions:
            relative_sigma = std_dev / abs(mean)
            standardized_position = (values[series_index] - mean) / std_dev if std_dev else 0
            relative_deviation = standardized_position * relative_sigma
            if inverse:
                relative_deviation = -relative_deviation
            radii.append(max(.05, min(.5 + 1.25 * relative_deviation, 1)))
        profiles.append(radii)
    return dimensions, profiles


def detail_kiviat_profiles(analyses: list[tuple[Path, object]], minimum_dispersion: float = 10.0):
    """Profils des mesures du tableau 2 dont σ atteint le seuil demandé."""
    rows_by_file = []
    numeric_maps = []
    for _, stats in analyses:
        _, details = split_rows(statistic_rows(stats))
        rows_by_file.append(details)
        numeric_maps.append(statistic_numeric_values(stats))
    dispersions = coefficient_dispersions(rows_by_file, numeric_maps)
    labels = [
        label for label, _ in rows_by_file[0]
        if (value := numeric_value(dispersions.get(label))) is not None and value >= minimum_dispersion
        and label != "Diversité de longueurs de phrase (mots)"
    ]
    dimensions = []
    for label in labels:
        values = [numeric[label] for numeric in numeric_maps if numeric.get(label) is not None]
        if len(values) != len(analyses):
            continue
        mean = sum(values) / len(values)
        if not mean:
            continue
        std_dev = math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))
        inverse = label in {
            "Répétition globale des trigrammes",
            "Répétition locale des trigrammes",
            "Adjectifs",
            "Adverbes",
            "Relatives",
            "Comparaisons métaphoriques",
        }
        dimensions.append((label, values, mean, std_dev, inverse, label.endswith("%")))
    profiles = []
    for series_index in range(len(analyses)):
        radii = []
        for _, values, mean, std_dev, inverse, _ in dimensions:
            relative_deviation = (values[series_index] - mean) / abs(mean)
            if inverse:
                relative_deviation = -relative_deviation
            radii.append(max(.05, min(.5 + 1.25 * relative_deviation, 1)))
        profiles.append(radii)
    return dimensions, profiles


def kiviat_chart(analyses: list[tuple[Path, object]], profile_data=None) -> str:
    """Compare les dimensions retenues à la moyenne du corpus."""
    dimensions, profiles = profile_data or kiviat_profiles(analyses)
    width, height = 1000, 780
    center_x, center_y, radius = 500, 355, 265
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:#222}.axis{font-size:13px}.legend{font-size:14px}.grid{fill:none;stroke:#ccd1d5;stroke-width:1}.spoke{stroke:#d9dddf;stroke-width:1}</style>',
    ]
    count = len(dimensions)
    if count < 3:
        parts.append('<text x="500" y="355" text-anchor="middle">Pas assez de dimensions variables</text></svg>')
        return "\n".join(parts)
    angles = [-math.pi / 2 + index * 2 * math.pi / count for index in range(count)]
    for level in (.1, .25, .5, .75, 1):
        points = " ".join(f"{center_x + radius * level * math.cos(angle):.1f},{center_y + radius * level * math.sin(angle):.1f}" for angle in angles)
        parts.append(f'<polygon class="grid" points="{points}"/>')
    for angle, (label, _, mean, _, _, is_percent) in zip(angles, dimensions):
        x, y = center_x + radius * math.cos(angle), center_y + radius * math.sin(angle)
        label_x, label_y = center_x + (radius + 45) * math.cos(angle), center_y + (radius + 45) * math.sin(angle)
        anchor = "middle" if abs(math.cos(angle)) < .25 else ("start" if math.cos(angle) > 0 else "end")
        parts.append(f'<line class="spoke" x1="{center_x}" y1="{center_y}" x2="{x:.1f}" y2="{y:.1f}"/>')
        parts.append(f'<text class="axis" x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="{anchor}">{html.escape(label)}</text>')
    # L’IA est tracée en dernier pour que sa courbe reste lisible par-dessus les autres séries.
    series_order = list(range(1, len(analyses))) + ([0] if analyses else [])
    for series_index in series_order:
        source, _ = analyses[series_index]
        points = []
        for angle, normalized in zip(angles, profiles[series_index]):
            x = center_x + radius * normalized * math.cos(angle)
            y = center_y + radius * normalized * math.sin(angle)
            points.append(f"{x:.1f},{y:.1f}")
        color = KIVIAT_COLORS[series_index % len(KIVIAT_COLORS)]
        stroke_width = 4 if series_index == 0 else 3
        fill_opacity = "0.15" if series_index == 0 else "0.09"
        parts.append(f'<polygon points="{" ".join(points)}" fill="{color}" fill-opacity="{fill_opacity}" stroke="{color}" stroke-width="{stroke_width}" stroke-opacity="0.88"/>')
    item_widths = [58 + len(display_name(source)) * 7 for source, _ in analyses]
    legend_gap = 18
    legend_width = sum(item_widths) + legend_gap * max(0, len(analyses) - 1)
    legend_x = (width - legend_width) / 2
    for index, (source, _) in enumerate(analyses):
        x, color = legend_x, KIVIAT_COLORS[index % len(KIVIAT_COLORS)]
        parts.append(f'<line x1="{x:.1f}" y1="745" x2="{x + 25:.1f}" y2="745" stroke="{color}" stroke-width="4"/>')
        parts.append(f'<text class="legend" x="{x + 33:.1f}" y="750">{html.escape(display_name(source))}</text>')
        legend_x += item_widths[index] + legend_gap
    parts.append("</svg>")
    return french_typography("\n".join(parts))


def bigfive_profiles(analyses: list[tuple[Path, object]]):
    """Construit les cinq axes BigFive, agrégés par auteur et normalisés au corpus."""
    dimensions = []
    for label, field in BIGFIVE_AXES:
        values = [float(getattr(stats, field, 0) or 0) for _, stats in analyses]
        maximum = max(values, default=0)
        normalized = [value / maximum if maximum else 0.0 for value in values]
        dimensions.append((label, normalized, sum(values) / (len(values) or 1), 0, False, True))
    profiles = [[max(.05, min(.05 + .90 * dimensions[index][1][series], 1)) for index in range(len(dimensions))] for series in range(len(analyses))]
    return dimensions, profiles


def author_analyses(sources, analyses):
    """Moyenne les œuvres d'un même auteur pour les graphiques du README."""
    authors = {}
    with sqlite3.connect(EPUB_DATABASE) as connection:
        for source, stats in analyses:
            row = connection.execute("SELECT author FROM books WHERE path = ?", (str(source.resolve()),)).fetchone()
            author = (row[0] if row and row[0] else source.stem).strip()
            authors.setdefault(author, []).append(stats)
    result = []
    for author in sorted(authors, key=str.casefold):
        values = authors[author]
        averaged = {}
        for field in fields(TextStats):
            numbers = [getattr(item, field.name) for item in values if isinstance(getattr(item, field.name), (int, float))]
            if numbers:
                averaged[field.name] = sum(numbers) / len(numbers)
        result.append((Path(author), TextStats(**averaged)))
    return result


def kiviat_area_chart(analyses: list[tuple[Path, object]], profile_data=None) -> str:
    """Histogramme des surfaces des profils du radar, en unités arbitraires."""
    _, profiles = profile_data or kiviat_profiles(analyses)
    count = len(profiles[0]) if profiles else 0
    angles = [-math.pi / 2 + index * 2 * math.pi / count for index in range(count)] if count else []
    areas = []
    for series_index, radii in enumerate(profiles):
        points = [(value * math.cos(angle), value * math.sin(angle)) for value, angle in zip(radii, angles)]
        area = abs(sum(
            x1 * y2 - x2 * y1
            for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1])
        )) / 2 if points else 0
        areas.append((area, series_index))
    areas.sort()
    width, row_height = 900, 58
    height = 70 + row_height * len(areas)
    label_x, bar_x, bar_width = 145, 170, 670
    maximum = max((area for area, _ in areas), default=1) or 1
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:#222}.title{font-size:20px;font-weight:700}.label{font-size:15px}</style>',
        '<text class="title" x="450" y="30" text-anchor="middle">Surface des profils du radar</text>',
    ]
    for row, (area, series_index) in enumerate(areas):
        y = 58 + row * row_height
        source, _ = analyses[series_index]
        color = KIVIAT_COLORS[series_index % len(KIVIAT_COLORS)]
        current_width = bar_width * area / maximum
        parts.append(f'<text class="label" x="{label_x}" y="{y + 22}" text-anchor="end">{html.escape(display_name(source))}</text>')
        parts.append(f'<rect x="{bar_x}" y="{y}" width="{current_width:.1f}" height="30" rx="4" fill="{color}" fill-opacity="0.72"/>')
    parts.append('</svg>')
    return french_typography("\n".join(parts))


def notes(titles: list[str]) -> list[str]:
    result = []
    for number, title in enumerate(titles, 1):
        content = note_section_for(title)
        if content is None:
            continue
        content = content.strip()
        result.extend([f"[^{number}]: {content}", ""])
    return result[:-1]


def display_name(source: Path) -> str:
    """Titre éditorial SQLite, avec le nom de fichier comme repli."""
    name = ""
    if EPUB_DATABASE.exists():
        try:
            with sqlite3.connect(EPUB_DATABASE) as connection:
                row = connection.execute("SELECT title FROM books WHERE path = ?", (str(source.resolve()),)).fetchone()
                name = (row[0] or "").strip() if row else ""
        except sqlite3.Error:
            name = ""
    if not name:
        name = source.stem.replace("_", " ").replace("-", " ")
        name = re.sub(r"(?<=\D)(\d+)$", r" \1", name)
        name = re.sub(r"\s+", " ", name).strip()
        name = name[:1].upper() + name[1:]
    return name


def report_display_name(source: Path) -> str:
    """Affiche explicitement le groupe IA dans les en-têtes du rapport."""
    name = display_name(source)
    if source.parent.resolve() != SOURCE_DIR.resolve():
        return name
    match = re.search(r"(?m)^author:\s*[\"']?([^\"'\n]+?)[\"']?\s*$", source.read_text(encoding=TEXT_ENCODING, errors="replace"))
    return f"IA — {name}" if match and match.group(1).strip().casefold() == "ia" else name


def markdown_stats(source: Path, stats) -> str:
    rows = statistic_rows(stats)
    important, details = split_rows(rows)
    numbered, note_titles = number_notes(important + details)
    important, details = numbered[:len(important)], numbered[len(important):]
    lines = [f"# Statistiques — {source.name}", "", "## Synthèse", ""]
    lines += markdown_table(["Valeur"], [important])
    lines += ["", "## Détails", ""]
    lines += markdown_table(["Valeur"], [details])
    lines += ["", "## Répartition grammaticale", ""]
    lines += grammatical_distribution_table(display_name(source), stats)
    lines += [""] + notes(note_titles)
    return french_typography("\n".join(lines))


def markdown_comparison(sources: list[Path], analyses: list[tuple[Path, object]] | None = None, window: int | None = None) -> str:
    documents = comparison_documents(sources)
    document_texts = {source: text for source, text in documents}
    if window is None:
        analyses, window = comparable_analyses(sources, analyses)
    repetitions = [
        {
            "window": window,
            "count": len(source_windows(document_texts[source], window)),
            "absolute": stats.absolute_repetition_rate,
            "filtered": stats.filtered_repetition_rate,
            "family": stats.family_repetition_rate,
            "phonetic": stats.phonetic_repetition_rate,
        }
        for source, stats in analyses
    ]
    headers = [report_display_name(source) for source, _ in analyses]
    rows_by_file = [statistic_rows(stats, repetition) for (_, stats), repetition in zip(analyses, repetitions)]
    numeric_maps = [statistic_numeric_values(stats, repetition) for (_, stats), repetition in zip(analyses, repetitions)]
    important_by_file, details_by_file = [], []
    for rows in rows_by_file:
        important, details = split_rows(rows)
        important_by_file.append(important)
        details_by_file.append(details)
    # Les volumes et longueurs sont conservés dans un tableau séparé : ils
    # décrivent le document, mais ne sont pas des mesures stylistiques.
    technical_by_file = []
    for rows in details_by_file:
        technical_by_file.append([row for row in rows if row[0] in TECHNICAL_LABELS and row[0] != "Fenêtres analysées"])
    details_by_file = [[row for row in rows if row[0] not in TECHNICAL_LABELS] for rows in details_by_file]
    secondary_by_file = [important + details for important, details in zip(important_by_file, details_by_file)]
    important_dispersions = coefficient_dispersions(important_by_file, numeric_maps)
    detail_dispersions = coefficient_dispersions(details_by_file, numeric_maps)
    secondary_dispersions = coefficient_dispersions(secondary_by_file, numeric_maps)
    if secondary_by_file:
        order = sorted(
            range(len(secondary_by_file[0])),
            key=lambda index: numeric_value(secondary_dispersions.get(secondary_by_file[0][index][0])) or -1,
            reverse=True,
        )
        secondary_by_file = [[rows[index] for index in order] for rows in secondary_by_file]
    bigfive_fields = [
        ("Classique / Contemporain", "classicism_score"),
        ("Maximaliste / Minimaliste", "baroque_score"),
        ("Narratif / Descriptif", "narrativity_score"),
        ("Émotionnel / Neutre", "emotionality_score"),
        ("Discursif / Immersif", "discursivite_score"),
    ]
    bigfive_by_file = [[(label, f"{getattr(stats, field) * 100:.1f} %") for label, field in bigfive_fields] for _, stats in analyses]
    bigfive_numeric = [{label: getattr(stats, field) * 100 for label, field in bigfive_fields} for _, stats in analyses]
    bigfive_dispersions = coefficient_dispersions(bigfive_by_file, bigfive_numeric)
    numbered, note_titles = number_notes(bigfive_by_file[0] + secondary_by_file[0] + technical_by_file[0], ["Dispersion"])
    bigfive_count = len(bigfive_by_file[0])
    number_map = {
        re.sub(r"\[\^\d+\]$", "", label): label
        for label, _ in numbered
    }
    bigfive_by_file = [[(number_map[label], value) for label, value in rows] for rows in bigfive_by_file]
    secondary_by_file = [[(number_map[label], value) for label, value in rows] for rows in secondary_by_file]
    technical_by_file = [[(number_map[label], value) for label, value in rows] for rows in technical_by_file]
    lines = [
        "# Comparaison statistique des sources", "",
        f"> Les mesures dérivées sont moyennées sur des fenêtres non chevauchantes d’environ {window} mots, arrêtées aux paragraphes. Gzip utilise des blocs UTF-8 de taille identique. Les nombres de mots, phrases et paragraphes décrivent le document complet.", "",
        "## Tableau 1 — BigFive", "",
        readme_text("BigFive"), "",
    ]
    lines += markdown_table(headers, bigfive_by_file, bigfive_dispersions)
    lines += ["", "## Tableau 2 — Mesures", ""]
    lines += markdown_table(headers, secondary_by_file, secondary_dispersions)
    lines += ["", "## Tableau 3 — Données", ""]
    lines += markdown_table(headers, technical_by_file)
    nearest = nearest_neighbor_markdown()
    if nearest:
        lines += [""] + nearest
    lines += ["", "## Profil comparatif", "", f"![Diagramme de Kiviat]({KIVIAT_CHART.name})", ""]
    lines += ["Le diagramme reprend exactement les mesures du tableau principal. L’anneau médian représente la moyenne du corpus avec le même gris que les autres lignes de lecture. Les écarts relatifs à cette moyenne sont amplifiés pour rendre les profils lisibles ; les répétitions lexicales sont inversées afin que l’extérieur indique toujours davantage de diversité ou de complexité.", ""]
    lines += ["", "## Surface des profils", "", f"![Surface des profils du radar]({KIVIAT_AREA_CHART.name})", ""]
    lines += ["Les surfaces sont calculées directement sur les polygones du radar et classées de la plus petite à la plus grande. Leur unité est arbitraire.", ""]
    lines += ["", "## Répartition grammaticale par document", "", f"![Répartition grammaticale]({GRAMMATICAL_DISTRIBUTION_CHART.name})", ""]
    lines += [""] + notes(note_titles)
    return french_typography("\n".join(lines))


def sync_readme(report: str, readme_path: Path = README_FILE) -> None:
    """Remplace l'instantané du README par le dernier rapport rendu."""
    readme = readme_path.read_text(encoding=TEXT_ENCODING)
    report_start = report.index("## Tableau 1 — BigFive")
    snapshot = report[report_start:]
    snapshot = re.sub(r"(?m)^## ", "### ", snapshot)
    snapshot = snapshot.replace(
        "![Diagramme de Kiviat](kiviat.svg)",
        "![Profils comparatifs](./assets/readme/kiviat-github.png)",
    ).replace(
        "![Radar des mesures secondaires](kiviat_details.svg)",
        "![Radar des mesures secondaires](./assets/readme/kiviat-details-github.png)",
    ).replace(
        "![Surface des profils du radar](kiviat_areas.svg)",
        "![Surface des profils](./assets/readme/kiviat-areas-github.png)",
    ).replace(
        "![Répartition grammaticale](grammatical_distribution.svg)",
        "![Répartition grammaticale](./assets/readme/grammatical-distribution-github.png)",
    )
    generated = (
        f"{README_STATS_START}\n"
        "## Dernier résultat\n\n"
        "Ces tableaux et leurs notes sont actualisés automatiquement par `./readme.sh`.\n\n"
        f"{snapshot.strip()}\n"
        f"{README_STATS_END}"
    )
    if README_STATS_START in readme and README_STATS_END in readme:
        before, remainder = readme.split(README_STATS_START, 1)
        _, after = remainder.split(README_STATS_END, 1)
        updated = before + generated + after
    else:
        start = readme.index("## Dernier résultat")
        end = readme.index("Une empreinte SHA-256", start)
        updated = readme[:start] + generated + "\n\n" + readme[end:]
    readme_path.write_text(updated, encoding=TEXT_ENCODING)


def svg_to_png(source: Path, destination: Path) -> bool:
    """Produit l'image GitHub avec ImageMagick lorsqu'il est disponible."""
    executable = shutil.which("magick") or shutil.which("convert")
    if executable is None:
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [executable, "-background", "white", "-density", "144", str(source), str(destination)],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return completed.returncode == 0


def markdown_structure_report(source: Path) -> str:
    sentences = split_structure_units(read_source(source))
    structures = sentence_structure_signatures(sentences)
    lines = [f"# Structures — {source.name}", "", "| # | Phrase | Structure |", "|---:|---|---|"]
    for index, (sentence, structure) in enumerate(zip(sentences, structures), 1):
        clean_sentence = re.sub(r"\s+", " ", sentence).replace("|", "\\|")
        if not structure_is_eligible(structure):
            displayed_structure = f"~~`{structure}`~~ (écartée)"
        else:
            displayed_structure = f"`{structure}`"
        lines.append(f"| {index} | {clean_sentence} | {displayed_structure} |")
    return "\n".join(lines)


def markdown_lemma_report(source: Path) -> str:
    """Version lemmatisée où les répétitions filtrées sont mises en gras."""
    text = read_source(source)
    tokens = tokenize_repetitions(text)
    annotations = repetition_lemma_annotations(tokens)
    parts = [
        f"# Lemmes et répétitions — {source.name}\n\n",
        "Les lemmes en gras appartiennent à une famille lexicale dont deux occurrences sont distantes d’au plus 300 mots. "
        "Les mots-outils sont lemmatisés mais ne sont pas signalés.\n\n",
    ]
    cursor = 0
    if tokens and isinstance(tokens[0], tuple):
        spans = [(token[3], token[4]) for token in tokens]
    else:
        normalized = text.replace("’", " ").replace("'", " ")
        spans = [(match.start(), match.end()) for match in WORD_RE.finditer(normalized) if len(match.group(0)) >= 2]
    for (start, end), (lemma, repeated) in zip(spans, annotations):
        parts.append(text[cursor:start])
        parts.append(f"**{lemma}**" if repeated else lemma)
        cursor = end
    parts.append(text[cursor:])
    return "".join(parts)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Statistiques stylistiques d’un texte français")
    parser.add_argument("source", nargs="?", help="fichier précis ; sans argument, compare tous les Markdown de sources")
    args = parser.parse_args(argv)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.source is None:
        sources = comparison_sources()
        if not sources:
            parser.error(f"aucun fichier {SOURCE_MARKDOWN_PATTERN} dans {SOURCE_DIR}")
        fingerprint = corpus_fingerprint(sources)
        # Le rapport de comparaison est une vue de SQLite ; il ne relance
        # jamais l'analyse des Markdown ni spaCy.
        cached = None
        if cached is not None:
            compared_analyses, window, stale_metrics = cached
            if stale_metrics <= set(METRIC_CACHE_VERSIONS):
                if stale_metrics:
                    compared_analyses = refresh_trigram_metrics(sources, compared_analyses, window)
                    write_comparison_cache(fingerprint, compared_analyses, window)
            else:
                cached = None
        if cached is not None:
            chart_analyses = author_analyses(sources, compared_analyses)
            chart_profile = bigfive_profiles(chart_analyses)
            KIVIAT_CHART.write_text(kiviat_chart(chart_analyses, chart_profile) + "\n", encoding=TEXT_ENCODING)
            KIVIAT_DETAIL_CHART.write_text(kiviat_chart(chart_analyses, chart_profile) + "\n", encoding=TEXT_ENCODING)
            KIVIAT_AREA_CHART.write_text(kiviat_area_chart(chart_analyses, chart_profile) + "\n", encoding=TEXT_ENCODING)
            svg_to_png(KIVIAT_DETAIL_CHART, README_KIVIAT_DETAIL_CHART)
            svg_to_png(KIVIAT_CHART, README_KIVIAT_CHART)
            svg_to_png(KIVIAT_AREA_CHART, README_KIVIAT_AREA_CHART)
            svg_to_png(GRAMMATICAL_DISTRIBUTION_CHART, README_GRAMMATICAL_CHART)
            comparison = markdown_comparison(sources, compared_analyses, window)
            STATS_COMPARISON_FILE.write_text(comparison + "\n", encoding=TEXT_ENCODING)
            sync_readme(comparison)
            if KIVIAT_DETAIL_CHART.exists() and not README_KIVIAT_DETAIL_CHART.exists():
                svg_to_png(KIVIAT_DETAIL_CHART, README_KIVIAT_DETAIL_CHART)
            print(STATS_COMPARISON_FILE)
            print(f"{len(sources)} fichiers comparés — cache utilisé")
            print(KIVIAT_CHART)
            print(KIVIAT_DETAIL_CHART)
            print(KIVIAT_AREA_CHART)
            print(GRAMMATICAL_DISTRIBUTION_CHART)
            return 0
        compared_analyses, window = sqlite_analyses(sources)
        comparison = markdown_comparison(sources, compared_analyses, window)
        STATS_COMPARISON_FILE.write_text(comparison + "\n", encoding=TEXT_ENCODING)
        sync_readme(comparison)
        chart_analyses = author_analyses(sources, compared_analyses)
        chart_profile = bigfive_profiles(chart_analyses)
        KIVIAT_CHART.write_text(kiviat_chart(chart_analyses, chart_profile) + "\n", encoding=TEXT_ENCODING)
        KIVIAT_DETAIL_CHART.write_text(kiviat_chart(chart_analyses, chart_profile) + "\n", encoding=TEXT_ENCODING)
        svg_to_png(KIVIAT_DETAIL_CHART, README_KIVIAT_DETAIL_CHART)
        KIVIAT_AREA_CHART.write_text(kiviat_area_chart(chart_analyses, chart_profile) + "\n", encoding=TEXT_ENCODING)
        GRAMMATICAL_DISTRIBUTION_CHART.write_text(grammatical_distribution_chart(compared_analyses) + "\n", encoding=TEXT_ENCODING)
        svg_to_png(KIVIAT_CHART, README_KIVIAT_CHART)
        svg_to_png(KIVIAT_AREA_CHART, README_KIVIAT_AREA_CHART)
        svg_to_png(GRAMMATICAL_DISTRIBUTION_CHART, README_GRAMMATICAL_CHART)
        print(STATS_COMPARISON_FILE)
        print(f"{len(sources)} fichiers comparés")
        print(KIVIAT_CHART)
        print(KIVIAT_DETAIL_CHART)
        print(KIVIAT_AREA_CHART)
        print(GRAMMATICAL_DISTRIBUTION_CHART)
        return 0
    source = Path(args.source)
    stats = compute_stats(read_source(source))
    markdown_output, json_output = output_paths(source)
    lemma_output = OUTPUT_DIR / f"{source.stem}{LEMMA_REPORT_SUFFIX}{MARKDOWN_EXTENSION}"
    markdown_output.write_text(markdown_stats(source, stats) + "\n", encoding=TEXT_ENCODING)
    lemma_output.write_text(markdown_lemma_report(source) + "\n", encoding=TEXT_ENCODING)
    payload = {"source": str(source), "stats": stats.to_metric_dict()}
    json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding=TEXT_ENCODING)
    print(markdown_output)
    print(json_output)
    print(lemma_output)
    print(f"{stats.word_count} mots")
    return 0
