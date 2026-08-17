"""Interface en ligne de commande des statistiques stylistiques."""

from dataclasses import asdict, fields, replace
from functools import lru_cache
from pathlib import Path
import argparse
import gzip
import hashlib
import html
import json
import math
import re

from .config import (
    JSON_EXTENSION,
    KIVIAT_CHART,
    KIVIAT_AREA_CHART,
    LEMMA_REPORT_SUFFIX,
    GRAMMATICAL_DISTRIBUTION_CHART,
    MARKDOWN_EXTENSION,
    OUTPUT_DIR,
    README_FILE,
    README_STATS_END,
    README_STATS_START,
    SOURCE_DIR,
    SOURCE_MARKDOWN_PATTERN,
    STATS_CACHE_MANIFEST,
    STATS_NOTES_FILE,
    STATS_COMPARISON_FILE,
    STATS_FILENAME_SUFFIX,
    STRUCTURE_REPORT_SUFFIX,
    TEXT_ENCODING,
)
from .stats import TextStats, WORD_RE, compute_stats, repetition_distribution, repetition_lemma_annotations, sentence_structure_signatures, split_sentences, split_structure_units, structure_is_eligible, tokenize, tokenize_repetitions


FULL_DOCUMENT_FIELDS = {
    "word_count", "unique_word_count", "sentence_count", "paragraph_count",
    "lexical_word_count", "unique_lemma_count", "relative_clause_count",
    "subordinate_clause_count", "nominal_sentence_count",
}


@lru_cache(maxsize=512)
def cached_compute_stats(text: str):
    return compute_stats(text)


def french_typography(text: str) -> str:
    """Applique l’espace insécable française avant le signe pour cent."""
    return text.replace(" %", "\u00a0%")


def normalize_source_text(text: str) -> str:
    """Ramène les suites de plus de deux sauts de ligne à une ligne vide."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\n(?:[ \t]*\n){2,}", "\n\n", text)


def read_source(source: Path) -> str:
    return normalize_source_text(source.read_text(encoding=TEXT_ENCODING))


def is_human_source(source: Path) -> bool:
    return source.stem.startswith("_")


def comparison_sources() -> list[Path]:
    """IA sans préfixe, puis humains préfixés `_`, chaque groupe alphabétique."""
    sources = list(SOURCE_DIR.glob(SOURCE_MARKDOWN_PATTERN))
    return sorted(sources, key=lambda source: (is_human_source(source), display_name(source).casefold()))


def comparison_documents(sources: list[Path]) -> list[tuple[Path, str]]:
    """Fusionne tous les textes IA dans un document virtuel unique nommé IA."""
    ai_texts = [read_source(source) for source in sources if not is_human_source(source)]
    documents = [(Path("IA.md"), "\n\n".join(text for text in ai_texts if text.strip()))] if ai_texts else []
    documents.extend((source, read_source(source)) for source in sources if is_human_source(source))
    return documents


def corpus_fingerprint(sources: list[Path]) -> str:
    """Empreinte du corpus, du code de calcul et des configurations éditables."""
    detector_dir = Path(__file__).resolve().parent
    paths = list(sources)
    paths.extend(sorted(detector_dir.glob("*.py")))
    paths.append(STATS_NOTES_FILE.parent / "function-words.txt")
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: str(item)):
        digest.update(str(path.resolve()).encode(TEXT_ENCODING))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def comparison_output_paths(sources: list[Path]) -> list[Path]:
    outputs = [STATS_COMPARISON_FILE, KIVIAT_CHART, KIVIAT_AREA_CHART, GRAMMATICAL_DISTRIBUTION_CHART]
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
        if manifest.get("fingerprint") != fingerprint:
            return None
        analyses = [
            (Path(item["source"]), TextStats(**item["stats"]))
            for item in manifest["analyses"]
        ]
        return analyses, int(manifest["window"])
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def write_comparison_cache(fingerprint: str, analyses, window: int) -> None:
    STATS_CACHE_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fingerprint": fingerprint,
        "window": window,
        "analyses": [
            {"source": str(source), "stats": asdict(stats)}
            for source, stats in analyses
        ],
    }
    STATS_CACHE_MANIFEST.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding=TEXT_ENCODING,
    )


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
    updates.update({
        "word_count": len(words),
        "unique_word_count": len(set(words)),
        "sentence_count": len(split_sentences(text)),
        "paragraph_count": len([part for part in re.split(r"\n\s*\n", text) if part.strip()]),
        "gzip_compression_ratio": gzip_window_ratio(text, gzip_window),
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
        ("Ratio noms/verbes", f"{stats.noun_verb_ratio:.2f}"),
        ("Diversité des structures[^4]", f"{stats.structural_diversity * 100:.0f} %"),
        ("Diversité de longueurs de phrase (mots)", f"{stats.sentence_word_std_dev:.1f}"),
        ("Rythme des structures[^14]", f"{stats.structural_rhythm * 100:.0f} %"),
        ("Compression gzip[^5]", f"{stats.gzip_compression_ratio * 100:.0f} %"),
        ("Relatives et subordonnées[^6]", f"{(stats.relative_clause_ratio + stats.subordinate_clause_ratio) * 100:.0f} %" if stats.relative_clause_ratio is not None and stats.subordinate_clause_ratio is not None else "indisponible"),
        ("Ponctuation (signes/300 mots)", f"{stats.punctuation_per_300_words:.1f}"),
        ("Diversité de ponctuation", f"{stats.punctuation_diversity * 100:.0f} %"),
        ("Phrases nominales[^15]", f"{stats.nominal_sentence_ratio * 100:.0f} %" if stats.nominal_sentence_ratio is not None else "indisponible"),
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
    "Ponctuation (signes/300 mots)",
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
    for line in path.read_text(encoding=TEXT_ENCODING).splitlines():
        if line.startswith("# "):
            current_title = line[2:].strip()
            sections[current_title] = []
        elif current_title is not None:
            sections[current_title].append(line)
    return {title: "\n".join(content).strip() for title, content in sections.items()}


def note_sections() -> dict[str, str]:
    return markdown_sections(STATS_NOTES_FILE)


def number_notes(rows: list[tuple[str, object]], prefix_titles: list[str] | None = None) -> tuple[list[tuple[str, object]], list[str]]:
    sections = note_sections()
    titles = (prefix_titles or []) + [label for label, _ in rows if label in sections]
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
        "Relatives et subordonnées": percent((stats.relative_clause_ratio or 0) + (stats.subordinate_clause_ratio or 0)),
        "Ponctuation (signes/300 mots)": stats.punctuation_per_300_words,
        "Diversité de ponctuation": percent(stats.punctuation_diversity),
        "Phrases nominales": percent(stats.nominal_sentence_ratio or 0),
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
    displayed_headers = headers + (["σ[^1]"] if dispersions is not None else [])
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
        ("Verbes", stats.pos_verb_ratio),
        ("Adjectifs", stats.pos_adjective_ratio),
        ("Adverbes", stats.pos_adverb_ratio),
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
        ("Adverbes", "pos_adverb_ratio", "#efb349"),
        ("Verbes", "pos_verb_ratio", "#ca4038"),
        ("Adjectifs", "pos_adjective_ratio", "#835692"),
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
        ("Ponctuation (signes/300 mots)", lambda s: s.punctuation_per_300_words, False, False),
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


def kiviat_chart(analyses: list[tuple[Path, object]]) -> str:
    """Compare les dimensions retenues à la moyenne du corpus."""
    dimensions, profiles = kiviat_profiles(analyses)
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


def kiviat_area_chart(analyses: list[tuple[Path, object]]) -> str:
    """Histogramme des surfaces des profils du radar, en unités arbitraires."""
    _, profiles = kiviat_profiles(analyses)
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
    sections = note_sections()
    result = []
    for number, title in enumerate(titles, 1):
        if title not in sections:
            continue
        content = sections[title].strip()
        result.extend([f"[^{number}]: {content}", ""])
    return result[:-1]


def display_name(source: Path) -> str:
    """Nom de colonne lisible : sans extension, capitale initiale, espace avant chiffres finaux."""
    name = source.stem.replace("_", " ").replace("-", " ")
    name = re.sub(r"(?<=\D)(\d+)$", r" \1", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:1].upper() + name[1:]


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
    headers = [display_name(source) for source, _ in analyses]
    rows_by_file = [statistic_rows(stats, repetition) for (_, stats), repetition in zip(analyses, repetitions)]
    numeric_maps = [statistic_numeric_values(stats, repetition) for (_, stats), repetition in zip(analyses, repetitions)]
    important_by_file, details_by_file = [], []
    for rows in rows_by_file:
        important, details = split_rows(rows)
        important_by_file.append(important)
        details_by_file.append(details)
    important_dispersions = coefficient_dispersions(important_by_file, numeric_maps)
    detail_dispersions = coefficient_dispersions(details_by_file, numeric_maps)
    numbered, note_titles = number_notes(important_by_file[0] + details_by_file[0], ["Dispersion"])
    important_count = len(important_by_file[0])
    number_map = {
        re.sub(r"\[\^\d+\]$", "", label): label
        for label, _ in numbered
    }
    important_by_file = [[(number_map[label], value) for label, value in rows] for rows in important_by_file]
    details_by_file = [[(number_map[label], value) for label, value in rows] for rows in details_by_file]
    lines = [
        "# Comparaison statistique des sources", "",
        f"> Les mesures dérivées sont moyennées sur des fenêtres non chevauchantes d’environ {window} mots, arrêtées aux paragraphes. Gzip utilise des blocs UTF-8 de taille identique. Les nombres de mots, phrases et paragraphes décrivent le document complet.", "",
        "## Synthèse", "",
    ]
    lines += markdown_table(headers, important_by_file, important_dispersions)
    lines += ["", "## Détails", ""]
    lines += markdown_table(headers, details_by_file, detail_dispersions)
    lines += ["", "## Profil comparatif", "", f"![Diagramme de Kiviat]({KIVIAT_CHART.name})", ""]
    lines += ["Le diagramme reprend exactement les mesures du tableau principal. L’anneau médian représente la moyenne du corpus avec le même gris que les autres lignes de lecture. Les écarts relatifs à cette moyenne sont amplifiés pour rendre les profils lisibles ; les répétitions lexicales sont inversées afin que l’extérieur indique toujours davantage de diversité ou de complexité.", ""]
    lines += ["", "## Surface des profils", "", f"![Surface des profils du radar]({KIVIAT_AREA_CHART.name})", ""]
    lines += ["Les surfaces sont calculées directement sur les polygones du radar et classées de la plus petite à la plus grande. Leur unité est arbitraire.", ""]
    lines += ["", "## Répartition grammaticale par document", "", f"![Répartition grammaticale]({GRAMMATICAL_DISTRIBUTION_CHART.name})", ""]
    lines += [""] + notes(note_titles)
    return french_typography("\n".join(lines))


def sync_readme(report: str, readme_path: Path = README_FILE) -> None:
    """Remplace l'instantané du README par le dernier rapport rendu."""
    readme = readme_path.read_text(encoding=TEXT_ENCODING)
    report_start = report.index("## Synthèse")
    snapshot = report[report_start:]
    snapshot = re.sub(r"(?m)^## ", "### ", snapshot)
    snapshot = snapshot.replace(
        "![Diagramme de Kiviat](kiviat.svg)",
        "![Profils comparatifs](./assets/readme/kiviat-github.png)",
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
        "Ces tableaux et leurs notes sont actualisés automatiquement par `./stats.sh`.\n\n"
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
        cached = read_comparison_cache(sources, fingerprint)
        if cached is not None:
            compared_analyses, window = cached
            comparison = markdown_comparison(sources, compared_analyses, window)
            STATS_COMPARISON_FILE.write_text(comparison + "\n", encoding=TEXT_ENCODING)
            sync_readme(comparison)
            print(STATS_COMPARISON_FILE)
            print(f"{len(sources)} fichiers comparés — cache utilisé")
            print(KIVIAT_CHART)
            print(KIVIAT_AREA_CHART)
            print(GRAMMATICAL_DISTRIBUTION_CHART)
            return 0
        compared_analyses, window = comparable_analyses(sources)
        comparison = markdown_comparison(sources, compared_analyses, window)
        STATS_COMPARISON_FILE.write_text(comparison + "\n", encoding=TEXT_ENCODING)
        sync_readme(comparison)
        KIVIAT_CHART.write_text(kiviat_chart(compared_analyses) + "\n", encoding=TEXT_ENCODING)
        KIVIAT_AREA_CHART.write_text(kiviat_area_chart(compared_analyses) + "\n", encoding=TEXT_ENCODING)
        GRAMMATICAL_DISTRIBUTION_CHART.write_text(grammatical_distribution_chart(compared_analyses) + "\n", encoding=TEXT_ENCODING)
        structure_reports = []
        lemma_reports = []
        for source in sources:
            report = OUTPUT_DIR / f"{source.stem}{STRUCTURE_REPORT_SUFFIX}{MARKDOWN_EXTENSION}"
            report.write_text(markdown_structure_report(source) + "\n", encoding=TEXT_ENCODING)
            structure_reports.append(report)
            lemma_report = OUTPUT_DIR / f"{source.stem}{LEMMA_REPORT_SUFFIX}{MARKDOWN_EXTENSION}"
            lemma_report.write_text(markdown_lemma_report(source) + "\n", encoding=TEXT_ENCODING)
            lemma_reports.append(lemma_report)
        write_comparison_cache(fingerprint, compared_analyses, window)
        print(STATS_COMPARISON_FILE)
        print(f"{len(sources)} fichiers comparés")
        print(KIVIAT_CHART)
        print(KIVIAT_AREA_CHART)
        print(GRAMMATICAL_DISTRIBUTION_CHART)
        for report in structure_reports:
            print(report)
        for report in lemma_reports:
            print(report)
        return 0
    source = Path(args.source)
    stats = compute_stats(read_source(source))
    markdown_output, json_output = output_paths(source)
    lemma_output = OUTPUT_DIR / f"{source.stem}{LEMMA_REPORT_SUFFIX}{MARKDOWN_EXTENSION}"
    markdown_output.write_text(markdown_stats(source, stats) + "\n", encoding=TEXT_ENCODING)
    lemma_output.write_text(markdown_lemma_report(source) + "\n", encoding=TEXT_ENCODING)
    payload = {"source": str(source), "stats": asdict(stats)}
    json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding=TEXT_ENCODING)
    print(markdown_output)
    print(json_output)
    print(lemma_output)
    print(f"{stats.word_count} mots")
    return 0
