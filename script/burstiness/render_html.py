"""
Construction du fichier HTML annoté : le Markdown source est reconstitué
tel quel (titres, listes, citations, blocs de code) mais les phrases
appartenant à une série de "burstiness" sont surlignées.
"""

import html
import re
from typing import List

from . import color_scale
from . import config
from . import length_metrics
from .sentence_split import Block, iter_blocks, split_sentences_batch
from .burst_detect import detect_bursts, run_index_for_sentence


def _escape(text: str) -> str:
    return html.escape(text, quote=False)


def _inline_md_to_html(text: str) -> str:
    """Rendu minimal des emphases Markdown (gras, italique, code, liens)."""
    text = _escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+?)`", r"<code>\1</code>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def _heading_level(prefix: str) -> int:
    return len(prefix.strip())


def build_html(
    md_text: str,
    threshold: int = config.RUN_THRESHOLD,
    k: float = config.LENGTH_TOLERANCE_K,
    mode: str = None,
    title: str = "Burstiness",
) -> str:
    mode = mode or config.LENGTH_MODE
    unit = length_metrics.unit_label(mode)
    blocks: List[Block] = list(iter_blocks(md_text))

    # 1) découpe de chaque bloc analysable en phrases, en UN SEUL passage
    #    spaCy (nlp.pipe) pour tout le document au lieu d'un appel par
    #    bloc — nettement plus rapide sur un document long. On garde la
    #    trace de la plage [start, end) que chaque bloc occupe dans la
    #    liste globale des phrases.
    analyzable = {"paragraph", "heading", "list_item", "blockquote"}
    block_texts = [b.text if (b.kind in analyzable and b.text.strip()) else "" for b in blocks]
    block_sentences: List[List[str]] = split_sentences_batch(block_texts)

    block_ranges: List[tuple] = []
    all_sentences: List[str] = []
    for sentences in block_sentences:
        start = len(all_sentences)
        all_sentences.extend(sentences)
        end = len(all_sentences)
        block_ranges.append((start, end))

    # 2) détection des séries sur l'ensemble du document (le fil de lecture
    #    traverse les paragraphes/listes/citations).
    counts, runs = detect_bursts(all_sentences, threshold=threshold, k=k, mode=mode)
    # Chaque série est entièrement autonome : sa couleur ne dépend QUE de
    # sa propre médiane interne, jamais du reste du document.
    run_local_medians = [color_scale.series_median(run) for run in runs]
    run_sentence_colors = [color_scale.colors_for_run(run) for run in runs]

    # 3) reconstruction du HTML bloc par bloc.
    out = []
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for b, sentences, (start, end) in zip(blocks, block_sentences, block_ranges):
        if b.kind != "list_item":
            close_list()

        if b.kind == "code":
            out.append(f"<pre class=\"md-code\"><code>{_escape(b.raw)}</code></pre>")
            continue

        if b.kind == "other":
            if b.raw.strip():
                out.append(f"<div class=\"md-hr\">{_escape(b.raw)}</div>")
            else:
                out.append("<div class=\"md-blank\"></div>")
            continue

        rendered_sentences = []
        for local_idx, sentence in enumerate(sentences):
            global_idx = start + local_idx
            run_k = run_index_for_sentence(runs, global_idx)
            sentence_html = _inline_md_to_html(sentence)
            syll = counts[global_idx]
            if run_k is not None:
                run = runs[run_k]
                position_in_run = global_idx - run.start  # 0 pour la 1ère phrase de la série
                color = run_sentence_colors[run_k][position_in_run]
                local_median = run_local_medians[run_k]
                range_txt = (
                    f"{run.min_count} {unit}"
                    if run.min_count == run.max_count
                    else f"{run.min_count}-{run.max_count} {unit}"
                )
                rendered_sentences.append(
                    f'<span class="burst" style="background-color:{color}" '
                    f'title="{syll} {unit} (médiane de SA série : {local_median:g}) - '
                    f'série #{run_k + 1}, phrase {position_in_run + 1}/{run.length} ({range_txt})">'
                    f"{sentence_html}</span>"
                    f'<sup class="len">{syll}</sup>'
                )
            else:
                rendered_sentences.append(
                    f'<span class="normal" title="{syll} {unit}">{sentence_html}</span>'
                    f'<sup class="len">{syll}</sup>'
                )
        inner = " ".join(rendered_sentences)

        if b.kind == "heading":
            level = min(max(_heading_level(b.prefix), 1), 6)
            out.append(f"<h{level}>{inner}</h{level}>")
        elif b.kind == "blockquote":
            out.append(f"<blockquote>{inner}</blockquote>")
        elif b.kind == "list_item":
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inner}</li>")
        else:  # paragraph
            out.append(f"<p>{inner}</p>")

    close_list()

    body = "\n".join(out)

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>{_escape(title)}</title>
<style>
  body {{
    font-family: Georgia, "Times New Roman", serif;
    max-width: 46em;
    margin: 2em auto;
    padding: 0 1.5em;
    line-height: 1.6;
    color: #1a1a1a;
  }}
  h1, h2, h3, h4, h5, h6 {{ font-family: Helvetica, Arial, sans-serif; }}
  .burst {{ border-radius: 3px; padding: 0.05em 0.15em; }}
  .normal {{ }}
  blockquote {{ border-left: 3px solid #ccc; margin-left: 0; padding-left: 1em; color: #555; }}
  pre.md-code {{ background: #f4f4f4; padding: 0.8em; overflow-x: auto; border-radius: 4px; }}
  .md-hr {{ color: #999; text-align: center; margin: 1.5em 0; }}
  sup.len {{ font-size: 0.6em; color: #999; margin-left: 0.1em; user-select: none; }}
</style>
</head>
<body>
{body}
</body>
</html>
"""
