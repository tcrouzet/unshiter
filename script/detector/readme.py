"""Synchronise dans le README la documentation des métriques du site."""

import re

from .config import METRICS, README_FILE, README_STATS_END, README_STATS_START, STATS_NOTES_FILE, TEXT_ENCODING


def documented_metrics() -> str:
    """Retourne les notes des métriques, sans la note générale de dispersion."""
    notes = STATS_NOTES_FILE.read_text(encoding=TEXT_ENCODING).strip()
    sections = re.split(r"(?=^# )", notes, flags=re.MULTILINE)
    metrics = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        match = re.search(r"\(([a-z][a-z0-9_]*)\)\s*$", section.splitlines()[0])
        if match and match.group(1) in METRICS:
            metrics.append(section)
    return "\n\n".join(re.sub(r"^# ", "### ", section, count=1) for section in metrics)


def main() -> int:
    readme = README_FILE.read_text(encoding=TEXT_ENCODING)
    if README_STATS_START not in readme or README_STATS_END not in readme:
        raise RuntimeError("Bornes de la section métriques absentes du README")
    before, remainder = readme.split(README_STATS_START, 1)
    _, after = remainder.split(README_STATS_END, 1)
    block = (
        f"{README_STATS_START}\n"
        "## Métriques\n\n"
        "Les résultats, tableaux et graphiques sont consultables exclusivement sur "
        "[l’application web](https://tcrouzet.github.io/unshiter/). "
        "La liste ci-dessous documente les mesures disponibles ; elle est générée depuis "
        "`assets/stats-notes.md`.\n\n"
        f"{documented_metrics()}\n"
        f"{README_STATS_END}"
    )
    README_FILE.write_text(before.rstrip() + "\n\n" + block + "\n" + after.lstrip(), encoding=TEXT_ENCODING)
    print(f"Métriques documentées dans {README_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
