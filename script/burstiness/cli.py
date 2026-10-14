"""
Point d'entrée : lit un fichier Markdown, génère le HTML annoté dans
``_wip``, et affiche son chemin.

Usage :
    python -m script.burstiness.cli chemin/source.md
"""

import argparse
from pathlib import Path

from . import config
from .render_html import build_html


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def generate(input_path: Path, output_dir: Path | None = None) -> Path:
    if not input_path.is_file() or input_path.suffix.casefold() != ".md":
        raise ValueError(f"Fichier Markdown introuvable : {input_path}")
    destination = output_dir or PROJECT_ROOT / "_wip"
    destination.mkdir(parents=True, exist_ok=True)
    output_path = destination / f"{input_path.stem}-burst.html"
    html_doc = build_html(input_path.read_text(encoding="utf-8"), title=input_path.stem)
    output_path.write_text(html_doc, encoding="utf-8")
    return output_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Visualise les séries de phrases de longueur proche")
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    try:
        print(generate(args.source))
    except ValueError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
