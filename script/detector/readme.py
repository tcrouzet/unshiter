"""Synchronise dans le README la documentation des métriques du site."""

import re

from .config import METRICS, README_FILE, README_STATS_END, README_STATS_START, STATS_NOTES_FILE, TEXT_ENCODING


def documented_metrics() -> str:
    """Retourne la documentation structurée, sans les notes d’interface."""
    kept = []
    skipping = False
    for line in STATS_NOTES_FILE.read_text(encoding=TEXT_ENCODING).splitlines():
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            identifier = re.search(r"\(([a-z][a-z0-9_]*)\)\s*$", heading.group(2))
            skipping = bool(identifier and identifier.group(1).startswith("note_"))
            if skipping:
                continue
            if heading.group(2) == "Lecture des résultats":
                continue
            if identifier:
                kept.append(f'<a id="{identifier.group(1)}"></a>')
        if not skipping:
            kept.append(line)
    return "\n".join(kept).strip()


def main() -> int:
    readme = README_FILE.read_text(encoding=TEXT_ENCODING)
    if README_STATS_START not in readme or README_STATS_END not in readme:
        raise RuntimeError("Bornes de la section métriques absentes du README")
    before, remainder = readme.split(README_STATS_START, 1)
    _, after = remainder.split(README_STATS_END, 1)
    block = (
        f"{README_STATS_START}\n"
        f"{documented_metrics()}\n"
        f"{README_STATS_END}"
    )
    README_FILE.write_text(before.rstrip() + "\n\n" + block + "\n" + after.lstrip(), encoding=TEXT_ENCODING)
    print(f"Métriques documentées dans {README_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
