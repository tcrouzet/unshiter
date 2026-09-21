"""
Point d'entrée : lit le fichier Markdown défini dans config.py, génère le
HTML annoté, et affiche son chemin.

Aucun paramètre en ligne de commande : tous les réglages (fichier source,
fichier de sortie, seuil, tolérance, mode syllabes/mots...) se modifient
dans config.py.

Usage :
    python -m script.burstiness.cli
"""

import pathlib
import sys

from . import config
from .render_html import build_html


def main() -> int:
    input_path = pathlib.Path(config.SOURCE_FILE)
    if not input_path.exists():
        print(f"Fichier introuvable : {input_path}", file=sys.stderr)
        return 1

    output_path = (
        pathlib.Path(config.OUTPUT_FILE) if config.OUTPUT_FILE else input_path.with_suffix(".html")
    )

    md_text = input_path.read_text(encoding="utf-8")
    html_doc = build_html(md_text, title=input_path.stem)
    output_path.write_text(html_doc, encoding="utf-8")

    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
