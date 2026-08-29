"""Construit la liste des noms à suffixe abstrait à examiner comme exceptions."""

from __future__ import annotations

import csv
from pathlib import Path

from .config import LEXIQUE_ARCHIVE, DICTIONARIES_DIR


SUFFIX_FILE = DICTIONARIES_DIR / "abstract-noun-suffixes.txt"
# Ne jamais écraser la liste éditée manuellement. Toute nouvelle extraction
# est volontairement écrite dans un fichier distinct à comparer ou fusionner.
OUTPUT_FILE = DICTIONARIES_DIR / "concrete-noun-exceptions_new.txt"


def load_suffixes() -> tuple[str, ...]:
    suffixes = []
    for line in SUFFIX_FILE.read_text(encoding="utf-8").splitlines():
        value = line.split(":", 1)[-1].strip().casefold()
        if value and not line.lstrip().startswith("#"):
            suffixes.append(value)
    return tuple(suffixes)


def build() -> int:
    suffixes = load_suffixes()
    rows: dict[str, float] = {}
    with LEXIQUE_ARCHIVE.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            ortho = (row.get("ortho") or "").strip().casefold()
            if (row.get("cgram") or "").strip().upper() != "NOM" or not ortho.endswith(suffixes):
                continue
            try:
                frequency = float((row.get("freqlivres") or "0").replace(",", "."))
            except ValueError:
                frequency = 0.0
            rows[ortho] = max(rows.get(ortho, 0.0), frequency)
    OUTPUT_FILE.write_text(
        "# Noms candidats aux exceptions de nominalisation, triés par freqlivres décroissant.\n"
        + "".join(f"{word}\n" for word, _ in sorted(rows.items(), key=lambda item: (-item[1], item[0])))
        , encoding="utf-8",
    )
    return len(rows)


if __name__ == "__main__":
    print(f"{build()} noms écrits dans {OUTPUT_FILE}")
