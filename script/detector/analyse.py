"""Produit un HTML montrant les passages retenus par une mesure."""

import argparse
import html
import heapq
from pathlib import Path

from .config import PROJECT_ROOT
from .epub_database import markdown_body
from .morphalou import contextual_lemma_map
from .stats import Metrics, _is_function_word


REPETITION_ANALYSES = {"repetition", "repetitions", "repetition_count"}


def _highlighted_text(text: str, ranges: tuple[tuple[int, int], ...]) -> str:
    parts = []
    cursor = 0
    text_length = max(len(text), 1)
    for index, (start, end) in enumerate(ranges):
        previous = "—" if index == 0 else f"-{(start - ranges[index - 1][0]) / text_length * 100:.1f} %"
        following = "—" if index == len(ranges) - 1 else f"+{(ranges[index + 1][0] - start) / text_length * 100:.1f} %"
        distance = f"Précédente : {previous} · Suivante : {following}"
        group = text[start:end].casefold()
        parts.append(html.escape(text[cursor:start], quote=False))
        parts.append(
            f'<mark tabindex="0" data-group="{html.escape(group, quote=True)}" data-distance="{html.escape(distance, quote=True)}" '
            f'title="{html.escape(distance, quote=True)}">{html.escape(text[start:end], quote=False)}</mark>'
        )
        cursor = end
    parts.append(html.escape(text[cursor:], quote=False))
    return "".join(parts)


def repetition_highlights(text: str, span: int = 1500) -> tuple[tuple[int, int, str, int], ...]:
    metrics = Metrics(text)
    tokens = metrics.contextual_tokens or []
    lemmas = contextual_lemma_map((word, category, lemma) for word, lemma, category, *_ in tokens)
    lexical = [
        (start, end, lemmas.get(word, lemma), word, category)
        for word, lemma, category, start, end in tokens
        if not _is_function_word(word, category, lemmas.get(word, lemma))
    ]
    repeated: set[int] = set()
    previous_by_lemma: dict[str, int] = {}
    for index, (start, _end, lemma, _word, _category) in enumerate(lexical):
        previous = previous_by_lemma.get(lemma)
        if previous is not None and start - lexical[previous][0] <= span:
            repeated.update((previous, index))
        previous_by_lemma[lemma] = index

    active: dict[str, tuple[int, int]] = {}
    free_colors: list[int] = []
    next_color = 0
    result = []
    for index in sorted(repeated):
        start, end, lemma, _word, _category = lexical[index]
        expired = [key for key, (_color, last) in active.items() if start - last > span]
        for key in expired:
            color, _last = active.pop(key)
            heapq.heappush(free_colors, color)
        if lemma in active:
            color = active[lemma][0]
        else:
            color = heapq.heappop(free_colors) if free_colors else next_color
            next_color = max(next_color, color + 1)
        active[lemma] = (color, start)
        result.append((start, end, lemma, color))
    return tuple(result)


def _repetition_text(text: str, highlights: tuple[tuple[int, int, str, int], ...]) -> str:
    parts = []
    cursor = 0
    text_length = max(len(text), 1)
    for index, (start, end, lemma, color) in enumerate(highlights):
        previous = "—" if index == 0 else f"-{(start - highlights[index - 1][0]) / text_length * 100:.1f} %"
        following = "—" if index == len(highlights) - 1 else f"+{(highlights[index + 1][0] - start) / text_length * 100:.1f} %"
        distance = f"{lemma} · Précédente : {previous} · Suivante : {following}"
        hue = round(color * 137.508 % 360)
        parts.append(html.escape(text[cursor:start], quote=False))
        parts.append(
            f'<mark tabindex="0" data-group="{html.escape(lemma, quote=True)}" data-distance="{html.escape(distance, quote=True)}" '
            f'title="{html.escape(distance, quote=True)}" style="background:hsl({hue} 85% 76%)">'
            f'{html.escape(text[start:end], quote=False)}</mark>'
        )
        cursor = end
    parts.append(html.escape(text[cursor:], quote=False))
    return "".join(parts)


def build_html(text: str, metric: str, title: str, repetition_span: int = 1500) -> str:
    if metric in REPETITION_ANALYSES:
        repetition_marks = repetition_highlights(text, repetition_span)
        ranges = tuple((start, end) for start, end, _lemma, _color in repetition_marks)
        value = len(repetition_marks)
        rendered_text = _repetition_text(text, repetition_marks)
        metric_label = f"répétitions lexicales à {repetition_span} caractères"
    else:
        metrics = Metrics(text)
        ranges_by_metric = {
            "stereotype_count": metrics.stereotype_ranges,
            "epistemic_hedging_count": metrics.epistemic_hedging_ranges,
            "ternary_count": metrics.ternary_ranges,
        }
        if metric not in ranges_by_metric:
            raise ValueError(f"Mesure non visualisable : {metric}")
        ranges = ranges_by_metric[metric]
        value = getattr(metrics, metric)()
        rendered_text = _highlighted_text(text, ranges)
        metric_label = metric
        if value != len(ranges):
            raise ValueError(f"Visualisation incohérente pour {metric}: {len(ranges)} surlignages, valeur {value}")
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
body {{ max-width: 52em; margin: 2em auto; padding: 0 1.5em; font: 18px/1.6 Georgia, serif; color: #1a1a1a; }}
h1, p.metric {{ font-family: Helvetica, Arial, sans-serif; }}
article {{ white-space: pre-wrap; }}
mark {{ background: #ffe36e; border-radius: 3px; padding: .05em .12em; cursor: pointer; }}
mark.selected {{ background: #111 !important; color: white; }}
#highlight-distance {{ position: fixed; right: 1.25rem; bottom: 5rem; padding: .45rem .7rem; border-radius: 4px; background: #1a1a1a; color: white; font: 14px/1.3 Helvetica, Arial, sans-serif; }}
#next-highlight {{ position: fixed; right: 1.25rem; bottom: 1.25rem; width: 3rem; height: 3rem; border: 0; border-radius: 50%; background: #1a1a1a; color: white; font-size: 1.5rem; cursor: pointer; }}
</style></head><body><h1>{html.escape(title)}</h1>
<p class="metric">{html.escape(metric_label)} : {value}</p>
<article>{rendered_text}</article>
<output id="highlight-distance" hidden></output>
<button id="next-highlight" type="button" aria-label="Surbrillance suivante">↓</button>
<script>
const highlights = [...document.querySelectorAll("mark")];
const distanceOutput = document.getElementById("highlight-distance");
let highlightIndex = -1;
let pinnedHighlight = null;
const selectGroup = highlight => {{
  const selected = highlight.classList.contains("selected");
  highlights.forEach(item => item.classList.toggle("selected", !selected && item.dataset.group === highlight.dataset.group));
  pinnedHighlight = selected ? null : highlight;
  if (pinnedHighlight) showDistance(pinnedHighlight);
  else distanceOutput.hidden = true;
}};
const showDistance = highlight => {{
  distanceOutput.textContent = highlight.dataset.distance;
  distanceOutput.hidden = false;
}};
highlights.forEach(highlight => {{
  highlight.addEventListener("mouseenter", () => showDistance(highlight));
  highlight.addEventListener("mouseleave", () => pinnedHighlight ? showDistance(pinnedHighlight) : distanceOutput.hidden = true);
  highlight.addEventListener("focus", () => showDistance(highlight));
  highlight.addEventListener("click", () => selectGroup(highlight));
}});
document.getElementById("next-highlight").addEventListener("click", () => {{
  if (!highlights.length) return;
  highlightIndex = (highlightIndex + 1) % highlights.length;
  const highlight = highlights[highlightIndex];
  highlights.forEach(item => item.classList.toggle("selected", item.dataset.group === highlight.dataset.group));
  pinnedHighlight = highlight;
  showDistance(highlight);
  highlight.scrollIntoView({{ behavior: "smooth", block: "center" }});
}});
</script></body></html>"""


def analyse_file(source: Path, metric: str, output_dir: Path | None = None, repetition_span: int = 1500) -> Path:
    if not source.is_file() or source.suffix.casefold() != ".md":
        raise ValueError(f"Fichier Markdown introuvable : {source}")
    destination = output_dir or PROJECT_ROOT / "_wip"
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / f"{source.stem}_{metric}.html"
    text = markdown_body(source.read_text(encoding="utf-8"))
    output.write_text(build_html(text, metric, source.stem, repetition_span), encoding="utf-8")
    return output.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Visualise les passages retenus par une mesure")
    parser.add_argument("source", type=Path)
    parser.add_argument("metric")
    parser.add_argument("span", type=int, nargs="?", default=1500)
    args = parser.parse_args()
    try:
        if args.span < 1:
            raise ValueError("L'empan doit être supérieur à zéro")
        print(analyse_file(args.source, args.metric, repetition_span=args.span))
    except ValueError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
