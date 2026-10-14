"""Produit un HTML montrant les passages retenus par une mesure."""

import argparse
import html
from pathlib import Path

from .config import PROJECT_ROOT
from .stats import Metrics


def _highlighted_text(text: str, ranges: tuple[tuple[int, int], ...]) -> str:
    parts = []
    cursor = 0
    text_length = max(len(text), 1)
    for index, (start, end) in enumerate(ranges):
        previous = "—" if index == 0 else f"-{(start - ranges[index - 1][0]) / text_length * 100:.1f} %"
        following = "—" if index == len(ranges) - 1 else f"+{(ranges[index + 1][0] - start) / text_length * 100:.1f} %"
        distance = f"Précédente : {previous} · Suivante : {following}"
        parts.append(html.escape(text[cursor:start], quote=False))
        parts.append(
            f'<mark tabindex="0" data-distance="{html.escape(distance, quote=True)}" '
            f'title="{html.escape(distance, quote=True)}">{html.escape(text[start:end], quote=False)}</mark>'
        )
        cursor = end
    parts.append(html.escape(text[cursor:], quote=False))
    return "".join(parts)


def build_html(text: str, metric: str, title: str) -> str:
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
    if value != len(ranges):
        raise ValueError(f"Visualisation incohérente pour {metric}: {len(ranges)} surlignages, valeur {value}")
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
body {{ max-width: 52em; margin: 2em auto; padding: 0 1.5em; font: 18px/1.6 Georgia, serif; color: #1a1a1a; }}
h1, p.metric {{ font-family: Helvetica, Arial, sans-serif; }}
article {{ white-space: pre-wrap; }}
mark {{ background: #ffe36e; border-radius: 3px; padding: .05em .12em; cursor: help; }}
#highlight-distance {{ position: fixed; right: 1.25rem; bottom: 5rem; padding: .45rem .7rem; border-radius: 4px; background: #1a1a1a; color: white; font: 14px/1.3 Helvetica, Arial, sans-serif; }}
#next-highlight {{ position: fixed; right: 1.25rem; bottom: 1.25rem; width: 3rem; height: 3rem; border: 0; border-radius: 50%; background: #1a1a1a; color: white; font-size: 1.5rem; cursor: pointer; }}
</style></head><body><h1>{html.escape(title)}</h1>
<p class="metric">{html.escape(metric)} : {value}</p>
<article>{_highlighted_text(text, ranges)}</article>
<output id="highlight-distance" hidden></output>
<button id="next-highlight" type="button" aria-label="Surbrillance suivante">↓</button>
<script>
const highlights = [...document.querySelectorAll("mark")];
const distanceOutput = document.getElementById("highlight-distance");
let highlightIndex = -1;
let pinnedHighlight = null;
const showDistance = highlight => {{
  distanceOutput.textContent = highlight.dataset.distance;
  distanceOutput.hidden = false;
}};
highlights.forEach(highlight => {{
  highlight.addEventListener("mouseenter", () => showDistance(highlight));
  highlight.addEventListener("mouseleave", () => pinnedHighlight ? showDistance(pinnedHighlight) : distanceOutput.hidden = true);
  highlight.addEventListener("focus", () => showDistance(highlight));
  highlight.addEventListener("click", () => {{ pinnedHighlight = highlight; showDistance(highlight); }});
}});
document.getElementById("next-highlight").addEventListener("click", () => {{
  if (!highlights.length) return;
  highlightIndex = (highlightIndex + 1) % highlights.length;
  pinnedHighlight = highlights[highlightIndex];
  showDistance(pinnedHighlight);
  pinnedHighlight.scrollIntoView({{ behavior: "smooth", block: "center" }});
}});
</script></body></html>"""


def analyse_file(source: Path, metric: str, output_dir: Path | None = None) -> Path:
    if not source.is_file() or source.suffix.casefold() != ".md":
        raise ValueError(f"Fichier Markdown introuvable : {source}")
    destination = output_dir or PROJECT_ROOT / "_wip"
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / f"{source.stem}.html"
    output.write_text(build_html(source.read_text(encoding="utf-8"), metric, source.stem), encoding="utf-8")
    return output.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Visualise les passages retenus par une mesure")
    parser.add_argument("source", type=Path)
    parser.add_argument("metric")
    args = parser.parse_args()
    try:
        print(analyse_file(args.source, args.metric))
    except ValueError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
