"""Réduit le dictionnaire émotionnel aux racines et locutions utiles."""

from collections import defaultdict

from .config import EMOTIONS_FILE, TEXT_ENCODING
from .demonette import family_map
from .morphalou import lemma_map
from .stats import tokenize


def main() -> int:
    sections: list[tuple[str, list[str]]] = []
    current: tuple[str, list[str]] | None = None
    for raw_line in EMOTIONS_FILE.read_text(encoding=TEXT_ENCODING).splitlines():
        line = raw_line.strip()
        if line.startswith("# ---"):
            current = (line, [])
            sections.append(current)
        elif line.startswith("lemme:") and current is not None:
            current[1].append(line.partition(":")[2].strip())

    entries = [(heading, value, tuple(tokenize(value))) for heading, values in sections for value in values]
    mapping = lemma_map(word for _, _, pattern in entries for word in pattern)
    normalized = [(heading, value, tuple(mapping.get(word, word) for word in pattern)) for heading, value, pattern in entries]
    families = family_map(word for _, _, pattern in normalized for word in pattern)

    retained_singles: dict[str, list[tuple[str, str]]] = defaultdict(list)
    used_families: dict[str, set[str]] = defaultdict(set)
    for heading, value, pattern in normalized:
        if len(pattern) != 1:
            continue
        lemma = pattern[0]
        lemma_families = set(families.get(lemma, ()))
        if lemma_families and lemma_families.intersection(used_families[heading]):
            continue
        retained_singles[heading].append((value, lemma))
        used_families[heading].update(lemma_families)

    all_single_lemmas = {lemma for values in retained_singles.values() for _, lemma in values}
    all_single_families = set().union(*(families.get(lemma, frozenset()) for lemma in all_single_lemmas))
    retained_phrases: dict[str, list[str]] = defaultdict(list)
    for heading, value, pattern in normalized:
        if len(pattern) <= 1:
            continue
        covered = any(
            lemma in all_single_lemmas
            or bool(families.get(lemma, frozenset()).intersection(all_single_families))
            for lemma in pattern
        )
        if not covered:
            retained_phrases[heading].append(value)

    blocks = []
    for heading, _ in sections:
        values = [value for value, _ in retained_singles[heading]] + retained_phrases[heading]
        blocks.append(heading + "\n\n" + "\n".join(f"lemme: {value}" for value in values))
    EMOTIONS_FILE.write_text("\n\n".join(blocks).rstrip() + "\n", encoding=TEXT_ENCODING)
    print(f"{len(entries)} entrées → {sum(len(values) for values in retained_singles.values())} racines + {sum(len(values) for values in retained_phrases.values())} locutions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
