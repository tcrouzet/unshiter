"""Génère les profils d'auteurs à partir de l'export statistique web."""
from __future__ import annotations

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "web" / "data.json"
OUTPUT = ROOT / "assets" / "style-descriptions.md"


def fmt(value: float) -> str:
    if abs(value - round(value)) < 0.005:
        return str(int(round(value)))
    return f"{value:.2f}"


def main() -> None:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    labels = payload.get("metric_labels", {})
    ids = payload.get("metric_note_ids", {})
    groups: dict[str, list[dict]] = {}
    for book in payload["books"]:
        groups.setdefault(book.get("author") or "Auteur inconnu", []).append(book)
    fields = list(labels)
    lines = [
        "# Profils stylistiques par auteur", "",
        "Ce document est généré à partir de toutes les mesures disponibles dans `web/data.json`. Pour chaque auteur, les colonnes indiquent le minimum, la médiane et le maximum observés sur ses œuvres. Les valeurs sont celles de la base, sans classement ni interprétation qualitative automatique.", "",
        "Les unités et définitions détaillées sont celles des notes identifiées par les numéros associés aux mesures dans le rapport statistique. Une seule œuvre produit trois valeurs identiques et ne permet pas d’estimer une dispersion entre œuvres.", "",
    ]
    for author in sorted(groups, key=lambda value: (value.casefold() != "ia", value.casefold())):
        books = groups[author]
        lines += [f"## {author}", "", f"Œuvres disponibles : {len(books)}", "", "| Mesure | Min. | Médiane | Max. |", "|---|---:|---:|---:|"]
        for field in fields:
            public_id = ids.get(field, field)
            values = []
            for book in books:
                value = book.get("analyses", [{}])[0].get("stats", {}).get(public_id)
                if isinstance(value, (int, float)):
                    values.append(float(value))
            if not values:
                continue
            lines.append(f"| {labels[field]} (`{public_id}`) | {fmt(min(values))} | {fmt(statistics.median(values))} | {fmt(max(values))} |")
        lines.append("")
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
