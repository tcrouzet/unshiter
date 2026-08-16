"""Interface en ligne de commande des statistiques stylistiques."""

from dataclasses import asdict, fields, replace
from pathlib import Path
import argparse
import html
import json
import math
import re

from .config import (
    JSON_EXTENSION,
    LEMMA_REPORT_SUFFIX,
    GRAMMATICAL_DISTRIBUTION_CHART,
    MARKDOWN_EXTENSION,
    OUTPUT_DIR,
    SOURCE_DIR,
    SOURCE_MARKDOWN_PATTERN,
    STATS_NOTES_FILE,
    STATS_COMPARISON_FILE,
    STATS_FILENAME_SUFFIX,
    STRUCTURE_REPORT_SUFFIX,
    STANDARD_DEVIATION_REFERENCE_STEMS,
    STANDARD_DEVIATION_MAXIMA,
    TEXT_ENCODING,
)
from .stats import WORD_RE, ai_score, compute_stats, repetition_distribution, repetition_lemma_annotations, sentence_structure_signatures, split_sentences, split_structure_units, structure_is_eligible, tokenize, tokenize_repetitions


FULL_DOCUMENT_FIELDS = {
    "word_count", "unique_word_count", "sentence_count", "paragraph_count",
    "lexical_word_count", "unique_lemma_count", "relative_clause_count",
    "subordinate_clause_count", "nominal_sentence_count",
}


def french_typography(text: str) -> str:
    """Applique l’espace insécable française avant le signe pour cent."""
    return text.replace(" %", "\u00a0%")


def source_windows(text: str, size: int) -> list[str]:
    """Fenêtres contiguës de même taille ; la dernière est alignée sur la fin."""
    tokens = list(WORD_RE.finditer(text))
    if not tokens or len(tokens) <= size:
        return [text]
    starts = list(range(0, len(tokens) - size + 1, size))
    if starts[-1] != len(tokens) - size:
        starts.append(len(tokens) - size)
    return [text[tokens[start].start():tokens[start + size - 1].end()] for start in starts]


def comparable_stats(text: str, full_stats, window: int):
    """Moyenne les mesures dérivées sur des fenêtres comparables."""
    samples = [compute_stats(fragment) for fragment in source_windows(text, window)]
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
    })
    return replace(base, **updates)


def comparable_analyses(sources: list[Path], analyses: list[tuple[Path, object]] | None = None):
    texts = [source.read_text(encoding=TEXT_ENCODING) for source in sources]
    window = min(len(tokenize(text)) for text in texts)
    full = analyses or [(source, None) for source in sources]
    compared = [
        (source, comparable_stats(text, stats, window))
        for (source, stats), text in zip(full, texts)
    ]
    return compared, window


def output_paths(source: Path) -> tuple[Path, Path]:
    stem = f"{source.stem}{STATS_FILENAME_SUFFIX}"
    return OUTPUT_DIR / f"{stem}{MARKDOWN_EXTENSION}", OUTPUT_DIR / f"{stem}{JSON_EXTENSION}"


def statistic_rows(stats, comparison: dict | None = None) -> list[tuple[str, object]]:
    percent = lambda value: f"{value * 100:.0f} %"
    score = ai_score(stats, stats.stylistic_repetition_rate)
    rows = [
        ("IA[^1]", f"{score} %" if score is not None else "indisponible"),
        ("Mots", stats.word_count), ("Phrases", stats.sentence_count), ("Paragraphes", stats.paragraph_count),
        ("Longueur moyenne des mots (caractères)", f"{stats.avg_word_length:.1f}"),
        ("Longueur moyenne des phrases (caractères)", f"{stats.avg_sentence_length:.1f}"),
        ("Longueur moyenne des phrases (mots)", f"{stats.avg_sentence_word_count:.1f}"),
        ("Longueur médiane des phrases (caractères)", f"{stats.median_sentence_length:.1f}"),
        ("Longueur P10 des phrases (caractères)", f"{stats.sentence_length_p10:.1f}"),
        ("Longueur P90 des phrases (caractères)", f"{stats.sentence_length_p90:.1f}"),
        ("Écart-type des phrases (caractères)", f"{stats.sentence_length_std_dev:.1f}"),
        ("Amplitude (caractères)", f"{stats.sentence_length_amplitude:.1f}"),
        ("Variation des phrases (mots)", f"{stats.sentence_word_std_dev:.1f}"),
        ("Burstiness[^2]", f"{stats.burstiness:.2f}"),
        ("Répétitions stylistiques[^9]", f"{stats.stylistic_repetition_rate * 100:.1f} %".replace(".", ",")),
        ("Répétitions lexicales[^10]", f"{(comparison['filtered'] if comparison else stats.filtered_repetition_rate) * 100:.0f} %"),
        ("Répétitions familiales[^11]", f"{(comparison['family'] if comparison else stats.family_repetition_rate) * 100:.0f} %"),
        ("Répétitions sonores[^12]", f"{(comparison['phonetic'] if comparison else stats.phonetic_repetition_rate) * 100:.0f} %"),
        ("Mots-outils[^13]", percent(stats.function_word_ratio)),
        ("Noms", f"{stats.noun_ratio * 100:.0f} %"),
        ("Verbes", f"{stats.verb_ratio * 100:.0f} %"),
        ("Adjectifs", f"{stats.adjective_ratio * 100:.0f} %"),
        ("Adverbes", f"{stats.adverb_ratio * 100:.0f} %"),
        ("Répétition des structures[^3]", f"{stats.structural_repetition_rate * 100:.0f} %"),
        ("Diversité des structures[^4]", f"{stats.structural_diversity * 100:.0f} %"),
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
        ("Diversité des formes", f"{stats.moving_type_token_ratio * 100:.0f} %"),
        ("Diversité lemmatisée", f"{stats.lemma_richness * 100:.0f} %"),
        ("Variété des débuts de phrase", f"{stats.sentence_start_diversity * 100:.0f} %"),
        ("Mots employés une seule fois", f"{stats.hapax_ratio * 100:.0f} %"),
        ("Répétition globale des trigrammes", f"{stats.trigram_repetition * 100:.0f} %"),
        ("Répétition locale des trigrammes", f"{stats.moving_trigram_repetition * 100:.0f} %"),
        ("Taux de répétition non filtré", f"{(comparison['absolute'] if comparison else stats.absolute_repetition_rate) * 100:.0f} %"),
        ("Fenêtres de répétition analysées", comparison["count"] if comparison else 1),
        ("Longueur moyenne des paragraphes (mots)", f"{stats.avg_paragraph_length:.1f}"),
    ]
    return rows


IMPORTANT_LABELS = {
    "IA",
    "Répétition des structures",
    "Diversité des structures",
    "Relatives et subordonnées",
    "Ponctuation (signes/300 mots)",
    "Diversité de ponctuation",
    "Variété des débuts de phrase",
    "Phrases nominales",
}

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
    "Écart-type des phrases (caractères)",
    "Écart-type des paragraphes (mots)",
    "Longueur moyenne des paragraphes (mots)",
    "Fenêtres de répétition analysées",
}


def split_rows(rows: list[tuple[str, object]]) -> tuple[list[tuple[str, object]], list[tuple[str, object]]]:
    rows = [(re.sub(r"\[\^\d+\]$", "", label), value) for label, value in rows]
    important = [row for row in rows if row[0] in IMPORTANT_LABELS]
    details = [row for row in rows if row[0] not in IMPORTANT_LABELS]
    details = (
        [row for row in details if row[0] not in TECHNICAL_LABELS]
        + [row for row in details if row[0] in TECHNICAL_LABELS]
    )
    return important, details


def note_sections() -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current_title = None
    for line in STATS_NOTES_FILE.read_text(encoding=TEXT_ENCODING).splitlines():
        if line.startswith("# "):
            current_title = line[2:].strip()
            sections[current_title] = []
        elif current_title is not None:
            sections[current_title].append(line)
    return {title: "\n".join(content).strip() for title, content in sections.items()}


def number_notes(rows: list[tuple[str, object]], prefix_titles: list[str] | None = None) -> tuple[list[tuple[str, object]], list[str]]:
    sections = note_sections()
    titles = (prefix_titles or []) + [label for label, _ in rows if label in sections]
    numbers = {title: index for index, title in enumerate(titles, 1)}
    return [
        (f"{label}[^{numbers[label]}]" if label in numbers else label, value)
        for label, value in rows
    ], titles


def normalized_range(values: list[object], maximum: float | None = None) -> str:
    """Écart IA–moyenne humaine rapporté au maximum possible ou observé."""
    numbers = []
    for value in values:
        match = re.search(r"-?\d+(?:[.,]\d+)?", str(value).replace(" ", ""))
        if match:
            numbers.append(float(match.group(0).replace(",", ".")))
    if len(numbers) != len(values) or not numbers:
        return "indisponible"
    if maximum is None and all("%" in str(value) for value in values):
        maximum = 100.0
    if maximum is None:
        maximum = max(abs(number) for number in numbers)
    if not maximum:
        return "0,0 %"
    if len(numbers) < 2:
        return "indisponible"
    human_mean = sum(numbers[1:]) / len(numbers[1:])
    gap = abs(numbers[0] - human_mean)
    return f"{gap / maximum * 100:.1f} %".replace(".", ",")


def markdown_table(headers: list[str], rows_by_file: list[list[tuple[str, object]]], show_deviation: bool = False, deviation_indexes: list[int] | None = None, deviation_maxima: dict[str, float] | None = None) -> list[str]:
    displayed_headers = headers + (["Δ[^1]"] if show_deviation else [])
    lines = ["| Mesure | " + " | ".join(displayed_headers) + " |", "|---|" + "---:|" * len(displayed_headers)]
    for index, (label, _) in enumerate(rows_by_file[0]):
        values = [str(rows[index][1]) for rows in rows_by_file]
        plain_label = re.sub(r"\[\^\d+\]$", "", label)
        reference_values = [values[index] for index in (deviation_indexes or range(len(values)))]
        deviation = [
            "—" if plain_label in TECHNICAL_LABELS else normalized_range(
                reference_values, (deviation_maxima or {}).get(plain_label, STANDARD_DEVIATION_MAXIMA.get(plain_label))
            )
        ] if show_deviation else []
        lines.append(f"| {label} | " + " | ".join(values + deviation) + " |")
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
    """SVG de camemberts horizontaux avec une légende commune."""
    categories = [
        ("Noms communs", "pos_common_noun_ratio", "#3d70a3"),
        ("Noms propres", "pos_proper_noun_ratio", "#75a843"),
        ("Adverbes", "pos_adverb_ratio", "#efb349"),
        ("Verbes", "pos_verb_ratio", "#ca4038"),
        ("Adjectifs", "pos_adjective_ratio", "#835692"),
    ]
    width, height = max(360 * len(analyses), 950), 430
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:#222}.title{font-size:20px;font-weight:700}.value{font-size:14px;font-weight:700;fill:white;paint-order:stroke;stroke:#333;stroke-width:3px}.legend{font-size:14px}</style>',
    ]
    for chart_index, (source, stats) in enumerate(analyses):
        center_x, center_y, radius = 180 + chart_index * 360, 175, 120
        parts.append(f'<text class="title" x="{center_x}" y="28" text-anchor="middle">{html.escape(display_name(source))}</text>')
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
    legend_width = len(categories) * 175
    legend_x = (width - legend_width) / 2
    for index, (label, _, color) in enumerate(categories):
        x = legend_x + index * 175
        parts.append(f'<rect x="{x:.1f}" y="375" width="16" height="16" rx="2" fill="{color}"/>')
        parts.append(f'<text class="legend" x="{x + 23:.1f}" y="388">{html.escape(label)}</text>')
    parts.append("</svg>")
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
    if window is None:
        analyses, window = comparable_analyses(sources, analyses)
    repetitions = [
        {
            "window": window,
            "count": len(source_windows(source.read_text(encoding=TEXT_ENCODING), window)),
            "absolute": stats.absolute_repetition_rate,
            "filtered": stats.filtered_repetition_rate,
            "family": stats.family_repetition_rate,
            "phonetic": stats.phonetic_repetition_rate,
        }
        for source, stats in analyses
    ]
    headers = [display_name(source) for source, _ in analyses]
    deviation_indexes = [
        index for index, (source, _) in enumerate(analyses)
        if source.stem in STANDARD_DEVIATION_REFERENCE_STEMS
    ]
    reference_stats = [analyses[index][1] for index in deviation_indexes]
    deviation_maxima = {
        "Variation des phrases (mots)": sum(stats.avg_sentence_word_count for stats in reference_stats) / len(reference_stats)
    }
    rows_by_file = [statistic_rows(stats, repetition) for (_, stats), repetition in zip(analyses, repetitions)]
    important_by_file, details_by_file = [], []
    for rows in rows_by_file:
        important, details = split_rows(rows)
        important_by_file.append(important)
        details_by_file.append(details)
    numbered, note_titles = number_notes(important_by_file[0] + details_by_file[0], ["Δ"])
    important_count = len(important_by_file[0])
    number_map = {
        re.sub(r"\[\^\d+\]$", "", label): label
        for label, _ in numbered
    }
    important_by_file = [[(number_map[label], value) for label, value in rows] for rows in important_by_file]
    details_by_file = [[(number_map[label], value) for label, value in rows] for rows in details_by_file]
    lines = [
        "# Comparaison statistique des sources", "",
        f"> Toutes les mesures dérivées sont moyennées sur des fenêtres de {window} mots, taille du texte le plus court. Les nombres de mots, phrases et paragraphes décrivent le document complet.", "",
        "## Synthèse", "",
    ]
    lines += markdown_table(headers, important_by_file, show_deviation=True, deviation_indexes=deviation_indexes, deviation_maxima=deviation_maxima)
    lines += ["", "## Détails", ""]
    lines += markdown_table(headers, details_by_file, show_deviation=True, deviation_indexes=deviation_indexes, deviation_maxima=deviation_maxima)
    lines += ["", "## Répartition grammaticale par document", "", f"![Répartition grammaticale]({GRAMMATICAL_DISTRIBUTION_CHART.name})", ""]
    lines += [""] + notes(note_titles)
    return french_typography("\n".join(lines))


def markdown_structure_report(source: Path) -> str:
    sentences = split_structure_units(source.read_text(encoding=TEXT_ENCODING))
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
    text = source.read_text(encoding=TEXT_ENCODING)
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
        sources = sorted(SOURCE_DIR.glob(SOURCE_MARKDOWN_PATTERN))
        if not sources:
            parser.error(f"aucun fichier {SOURCE_MARKDOWN_PATTERN} dans {SOURCE_DIR}")
        compared_analyses, window = comparable_analyses(sources)
        STATS_COMPARISON_FILE.write_text(markdown_comparison(sources, compared_analyses, window) + "\n", encoding=TEXT_ENCODING)
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
        print(STATS_COMPARISON_FILE)
        print(f"{len(sources)} fichiers comparés")
        print(GRAMMATICAL_DISTRIBUTION_CHART)
        for report in structure_reports:
            print(report)
        for report in lemma_reports:
            print(report)
        return 0
    source = Path(args.source)
    stats = compute_stats(source.read_text(encoding=TEXT_ENCODING))
    markdown_output, json_output = output_paths(source)
    lemma_output = OUTPUT_DIR / f"{source.stem}{LEMMA_REPORT_SUFFIX}{MARKDOWN_EXTENSION}"
    markdown_output.write_text(markdown_stats(source, stats) + "\n", encoding=TEXT_ENCODING)
    lemma_output.write_text(markdown_lemma_report(source) + "\n", encoding=TEXT_ENCODING)
    score = ai_score(stats)
    payload = {"source": str(source), "ai_score": score, "stats": asdict(stats)}
    json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding=TEXT_ENCODING)
    print(markdown_output)
    print(json_output)
    print(lemma_output)
    print(f"IA {score if score is not None else 'indisponible'} — {stats.word_count} mots")
    return 0
