#!/usr/bin/env python3
"""Propose des dates de première publication à partir de Wikipédia/Wikidata.

Le script complète automatiquement assets/publication.yml. Avec
--dry-run, il affiche seulement les propositions. Les résultats ambigus restent
vides et ne sont jamais transformés en date arbitraire.

Garantie éditoriale : une entrée déjà présente n'est jamais modifiée. Le
script peut seulement ajouter une nouvelle clé ou de nouveaux champs à une
nouvelle clé ; les corrections manuelles existantes sont intouchables.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import unicodedata
from pathlib import Path

import certifi
from detector.config import WIKIPEDIA_CACHE_FILE

ROOT = Path(__file__).resolve().parents[1]
EPUB_DIR = ROOT / "_epub"
DATES_FILE = ROOT / "assets" / "publication.yml"
YEAR_RE = re.compile(r"^[+-](\d{4})")
LAST_REQUEST = 0.0
_loaded_cache = json.loads(WIKIPEDIA_CACHE_FILE.read_text(encoding="utf-8")) if WIKIPEDIA_CACHE_FILE.exists() else {}
CACHE = _loaded_cache if "http" in _loaded_cache and "authors" in _loaded_cache else {"http": _loaded_cache, "authors": {}}


def save_cache() -> None:
    WIKIPEDIA_CACHE_FILE.write_text(json.dumps(CACHE, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get_json(url: str) -> dict:
    if url in CACHE["http"]:
        return CACHE["http"][url]
    global LAST_REQUEST
    delay = 1.1 - (time.monotonic() - LAST_REQUEST)
    if delay > 0:
        time.sleep(delay)
    request = urllib.request.Request(url, headers={"User-Agent": "unshiter-publication-dates/1.0 (contact: tcrouzet.com)"})
    context = ssl.create_default_context(cafile=certifi.where())
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=15, context=context) as response:
                LAST_REQUEST = time.monotonic()
                data = json.load(response)
                CACHE["http"][url] = data
                save_cache()
                return data
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("réponse Wikipédia impossible")


def front_matter(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    block = text.split("---", 2)[1] if text.startswith("---") else ""
    title = re.search(r'^title:\s*["\']?(.*?)["\']?\s*$', block, re.MULTILINE)
    author = re.search(r'^author:\s*["\']?(.*?)["\']?\s*$', block, re.MULTILINE)
    return (title.group(1).strip() if title else path.stem, author.group(1).strip() if author else "")


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def search_page(query: str, expected: str | None = None) -> tuple[int, str] | None:
    search_url = "https://fr.wikipedia.org/w/api.php?" + urllib.parse.urlencode({"action": "query", "list": "search", "srsearch": query, "srlimit": 5, "format": "json"})
    data = get_json(search_url)
    results = data.get("query", {}).get("search", [])
    if results:
        if expected:
            wanted = normalize(expected)
            exact = next((item for item in results if normalize(item["title"]) == wanted), None)
            if exact:
                return exact["pageid"], exact["title"]
        return results[0]["pageid"], results[0]["title"]
    return None


def wikidata_entity(page_id: int) -> dict | None:
    page = get_json("https://fr.wikipedia.org/w/api.php?" + urllib.parse.urlencode({"action": "query", "pageids": page_id, "prop": "pageprops", "format": "json"}))
    pages = page.get("query", {}).get("pages", {})
    qid = next(iter(pages.values()), {}).get("pageprops", {}).get("wikibase_item")
    return get_json(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json").get("entities", {}).get(qid) if qid else None


def entity_year(entity: dict) -> str | None:
    years = []
    for claim in entity.get("claims", {}).get("P577", []):
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("time", "")
        match = YEAR_RE.match(value)
        if match:
            years.append(match.group(1))
    return min(years) if years else None


def wikidata_date(title: str, author: str) -> str | None:
    # 1. Cherche l'auteur, puis ses œuvres déclarées dans Wikidata (P800).
    author_key = normalize(author)
    title_key = normalize(title)
    cached_author = CACHE["authors"].get(author_key)
    if cached_author is not None:
        return cached_author.get("works", {}).get(title_key)
    author_page = search_page(f'"{author}"', expected=author) if author else None
    if author_page:
        author_entity = wikidata_entity(author_page[0])
        author_cache = {"page_id": author_page[0], "page_title": author_page[1], "works": {}}
        for claim in (author_entity or {}).get("claims", {}).get("P800", []):
            qid = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id")
            if not qid:
                continue
            work = get_json(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json").get("entities", {}).get(qid, {})
            labels = [item.get("value", "") for item in work.get("labels", {}).values()]
            date = entity_year(work)
            for label in labels:
                if date:
                    author_cache["works"][normalize(label)] = date
        CACHE["authors"][author_key] = author_cache
        save_cache()
        return author_cache["works"].get(title_key)
    # Aucun recours à une recherche directe du titre : sans page auteur et
    # bibliographie exploitable, la date reste volontairement introuvable.
    CACHE["authors"][author_key] = {"page_id": None, "page_title": None, "works": {}}
    save_cache()
    return None


def read_existing() -> dict[str, dict[str, str]]:
    result = {}
    if DATES_FILE.exists():
        for line in DATES_FILE.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^([^:#]+\.epub):\s*[\"']?(.*?)[\"']?\s*$", line)
            if match:
                value = match.group(2).strip()
                date = re.search(r"\bdate\s*:\s*[\"']([^\"']*)[\"']", value)
                key = match.group(1).strip()
                title = re.search(r"\btitle\s*:\s*['\"]([^'\"]*)['\"]", value)
                author = re.search(r"\bauthor\s*:\s*['\"]([^'\"]*)['\"]", value)
                result[key] = {
                    "date": date.group(1) if date else value.strip('"\''),
                    "title": title.group(1) if title else "",
                    "author": author.group(1) if author else "",
                }
    return result


def source_authors(overrides: dict[str, dict[str, str]] | None = None) -> dict[str, str]:
    """Retourne l'auteur déclaré dans chaque Markdown extrait.

    L'auteur n'est pas dupliqué dans publication.yml : il reste une donnée
    éditoriale du livre et sert uniquement à ordonner le fichier de dates.
    """
    authors = {}
    for md in EPUB_DIR.glob("*.md"):
        _title, author = front_matter(md)
        key = md.with_suffix(".epub").name
        authors[key] = (overrides or {}).get(key, {}).get("author") or author.strip() or "Auteur inconnu"
    # Rattache les formes abrégées à la forme complète disponible
    # (par exemple « Caza » -> « Philippe Caza »), sans liste de cas spéciaux.
    names = list(set(authors.values()))
    frequencies = Counter(authors.values())
    canonical = {}
    for name in names:
        name_tokens = frozenset(normalize(name).split())
        equivalent = [other for other in names if frozenset(normalize(other).split()) == name_tokens]
        if len(equivalent) > 1:
            # En cas de permutation prénom/nom, la forme la plus représentée
            # dans le corpus devient la référence.
            canonical[name] = max(equivalent, key=lambda value: (frequencies[value], len(value)))
            continue
        tokens = set(normalize(name).split())
        candidates = [other for other in names if other != name and tokens and tokens < set(normalize(other).split())]
        canonical[name] = max(candidates, key=lambda value: len(normalize(value).split())) if candidates else name
    return {key: canonical.get(value, value) for key, value in authors.items()}


def date_sort_key(value: str) -> tuple[int, str]:
    """Trie les dates connues chronologiquement, les absences à la fin."""
    match = re.search(r"\d{4}", value or "")
    return (int(match.group()) if match else 9999, value or "")


def render_dates(entries: dict[str, dict[str, str]], authors: dict[str, str]) -> str:
    """Rend publication.yml groupé par auteur, puis par date."""
    groups: dict[str, list[tuple[str, dict[str, str]]]] = {}
    for key, item in entries.items():
        author = authors.get(key, item.get("author", "Auteur inconnu")) or "Auteur inconnu"
        groups.setdefault(author, []).append((key, item))
    lines = [
        "# Dates vérifiées ou complétées depuis Wikipédia/Wikidata.",
        "# Clé : nom du fichier EPUB normalisé ; valeur : année ou date complète.",
    ]
    for author in sorted(groups, key=lambda value: normalize(value)):
        lines.append("")
        lines.append(f"# {author}")
        for key, item in sorted(groups[author], key=lambda pair: (date_sort_key(pair[1].get("date", "")), normalize(pair[0]))):
            date = item.get("date", "")
            title = item.get("title", "")
            override_author = item.get("author", "")
            suffix = f', title: "{title}"' if title else ""
            if override_author:
                suffix += f', author: "{override_author}"'
            lines.append(f'{key}: {{date: "{date}"{suffix}}}')
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="n'écrit pas le fichier de dates")
    args = parser.parse_args()
    existing = read_existing()
    updates = {}
    for md in sorted(EPUB_DIR.glob("*.md")):
        title, author = front_matter(md)
        key = md.with_suffix(".epub").name
        # Une clé déjà présente, y compris avec une date vide, a été vérifiée
        # précédemment. Ne pas relancer inutilement la recherche à chaque
        # exécution d'epubs.sh ; supprimer la clé pour demander une nouvelle
        # recherche volontairement.
        if key in existing:
            # Les références déjà présentes ne sont pas réaffichées : une
            # date vide signifie qu'une recherche a déjà échoué et ne doit pas
            # polluer chaque lancement d'epubs.sh.
            continue
        try:
            date = wikidata_date(title, author)
        except Exception as error:
            print(f"{key}: erreur réseau ({error})", file=sys.stderr)
            date = None
        print(f"{key}: {date or '(introuvable)'} — {title}")
        # Même une absence de résultat est mémorisée afin de ne pas interroger
        # à nouveau Wikipédia au prochain lancement.
        updates[key] = date or ""
    if not args.dry_run:
        merged = dict(existing)
        for key, date in updates.items():
            # Les mises à jour ne concernent que des clés absentes : ne jamais
            # écraser une date, un titre ou un auteur saisi manuellement.
            if key not in merged:
                merged[key] = {"date": date}
        for key, item in existing.items():
            for field in ("date", "title", "author"):
                if merged.get(key, {}).get(field, "") != item.get(field, ""):
                    raise RuntimeError(f"Protection publication.yml : champ existant modifié ({key}.{field})")
        rendered = render_dates(merged, source_authors(merged))
        previous = DATES_FILE.read_text(encoding="utf-8") if DATES_FILE.exists() else ""
        if rendered != previous:
            DATES_FILE.write_text(rendered, encoding="utf-8")
            print(f"Écrit : {DATES_FILE}")
        elif not updates:
            print("Aucune nouvelle référence de date : fichier inchangé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
