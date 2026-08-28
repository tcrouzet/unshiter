#!/usr/bin/env python3
"""Extrait le texte et la couverture des EPUB vers _epub/*.md et *.avif."""

from __future__ import annotations

from html import unescape
from html.parser import HTMLParser
from pathlib import Path
import argparse
import hashlib
import json
import posixpath
import re
import shutil
import subprocess
import tempfile
import unicodedata
import zipfile
import xml.etree.ElementTree as ET

from detector.config import EPUB_ANALYSIS_WINDOW_SIZE, EPUB_DIR, EPUB_HASH_CACHE_FILE, PUBLICATION_FILE, TEXT_ENCODING


SKIP_DOCUMENT_WORDS = ("cover", "titlepage", "toc", "nav", "copyright", "imprint", "colophon")
TOC_FRONT_WORDS = ("couverture", "page de titre", "titre", "copyright", "auteur", "playlist", "du même auteur", "avertissement", "avant-propos", "mentions légales", "table des matières")
NUMBERED_TOC = re.compile(r"^(?:chapitre\s+)?\d+[.)]\s|\s-\s\d+\s-\s", re.I)
SKIP_TAGS = {"script", "style", "svg", "nav"}
CHAPTER_HEADING = re.compile(r"^#+\s*(?:(?:chapitre|partie|chapter)\s+)?(?:\d+|[ivxlcdm]+)\s*$", re.I)
UNKNOWN_PARAGRAPH = re.compile(r"^inconnu\s*\(e\)\s*$", re.I)
COPYRIGHT_YEAR = re.compile(r"(?:©|copyright|droits réservés|tous droits)[^\n]{0,180}?\b((?:19|20)\d{2})\b", re.I)
COMMON_GIVEN_NAMES = {
    "thierry", "jean", "marie", "pierre", "paul", "michel", "philippe",
    "françois", "francois", "christophe", "sophie", "isabelle", "anne",
    "claude", "nicolas", "olivier", "yannick", "laurent", "jacques",
}


class ShortEpubError(RuntimeError):
    """EPUB dont le texte narratif est trop court pour une fenêtre d'analyse."""

    def __init__(self, source: Path, length: int, minimum: int):
        self.source = source
        self.length = length
        self.minimum = minimum
        super().__init__(
            f"{source.name} : texte extrait de {length:,} signes, "
            f"minimum requis {minimum:,} ; Markdown non généré"
        )


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def text_value(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return " ".join("".join(element.itertext()).split())


class XHTMLText(HTMLParser):
    """Convertit le XHTML en paragraphes lisibles sans dépendance externe."""

    block_tags = {"p", "div", "section", "article", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6", "li", "br"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.current: list[str] = []
        self.skip_depth = 0
        self.in_body = False
        self.current_block = ""
        self.current_prefix = ""
        self.quote_depth = 0
        self.last_was_heading = False
        self.current_is_subtitle = False

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "body":
            self.in_body = True
            return
        if not self.in_body:
            return
        if tag == "blockquote":
            self.quote_depth += 1
        if tag == "hr":
            self.flush()
            self.parts.append("---")
            return
        if tag in SKIP_TAGS:
            self.skip_depth += 1
        if tag in self.block_tags and self.current:
            self.flush()
        if tag in self.block_tags:
            self.current_block = tag
            if tag in {"h1", "h2"}:
                self.current_prefix = "#"
            elif tag in {"h3", "h4"}:
                self.current_prefix = "##"
            else:
                self.current_prefix = ""
            if tag == "p" and self.last_was_heading and dict(attrs).get("class"):
                self.current_prefix = "##"
                self.current_is_subtitle = True
            if self.quote_depth:
                self.current_prefix = ">"

    def handle_startendtag(self, tag, attrs):
        if self.in_body and tag.lower() == "hr":
            self.flush()
            self.parts.append("---")
        elif self.in_body and tag.lower() in self.block_tags:
            self.flush()

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "body":
            self.flush()
            self.in_body = False
            return
        if not self.in_body:
            return
        if tag == "blockquote" and self.quote_depth:
            self.quote_depth -= 1
        if tag in SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
        if tag in self.block_tags:
            self.flush(self.current_prefix)
            self.last_was_heading = self.current_block in {"h1", "h2", "h3", "h4", "h5", "h6"}
            self.current_block = ""
            self.current_prefix = ""
            self.current_is_subtitle = False

    def handle_data(self, data):
        if self.in_body and not self.skip_depth:
            value = re.sub(r"\s+", " ", data)
            if not value.strip():
                if self.current and not self.current[-1].endswith(" "):
                    self.current[-1] += " "
                return
            if self.current and not value.startswith(" ") and not self.current[-1].endswith(" "):
                # Deux fragments inline contigus (« M » + « i-mars ») ne
                # forment pas deux mots : ne pas inventer d'espace.
                self.current[-1] += value
            else:
                self.current.append(value.strip())

    def flush(self, prefix: str = ""):
        value = re.sub(r"\s+", " ", " ".join(self.current)).strip()
        if self.current_is_subtitle and not self._short_subtitle(value):
            prefix = ""
        if value and not UNKNOWN_PARAGRAPH.match(value):
            self.parts.append(f"{prefix} {value}".strip() if prefix else value)
        self.current.clear()

    def result(self) -> str:
        self.flush()
        paragraphs = []
        for part in self.parts:
            if part.strip() == "*":
                part = "---"
            if paragraphs and paragraphs[-1].lstrip().startswith("> ") and self._looks_like_attribution(part):
                part = "> " + part
            if not paragraphs or part != paragraphs[-1]:
                paragraphs.append(part)
        return "\n\n".join(paragraphs)

    @staticmethod
    def _short_subtitle(value: str) -> bool:
        return (
            1 <= len(value) <= 120
            and len(value.split()) <= 15
            and not re.search(r"[.!?;:]$", value)
        )

    @staticmethod
    def _looks_like_attribution(value: str) -> bool:
        """Repère une ligne d'attribution immédiatement après une citation."""
        clean = value.strip()
        return (
            3 <= len(clean) <= 120
            and "," in clean
            and not re.search(r"[.!?;:]$", clean)
            and not clean.startswith(("#", ">", "---"))
        )


def package_root(archive: zipfile.ZipFile) -> tuple[str, ET.Element]:
    container = ET.fromstring(archive.read("META-INF/container.xml"))
    rootfile = next(element for element in container.iter() if local_name(element.tag) == "rootfile")
    path = rootfile.attrib["full-path"]
    return path, ET.fromstring(archive.read(path))


def metadata(package: ET.Element) -> dict[str, str]:
    result = {
        "title": "",
        "author": "",
        "author_firstname": "",
        "author_lastname": "",
        "publisher": "",
        "genre": "",
        "publication_date": "",
    }
    subjects, types, dates = [], [], []
    for element in package.iter():
        name = local_name(element.tag)
        value = text_value(element)
        if name == "title" and not result["title"]:
            result["title"] = value
        elif name in {"creator", "author"} and not result["author"]:
            result["author"] = value
        elif name == "publisher" and not result["publisher"]:
            result["publisher"] = value
        elif name == "subject" and value:
            subjects.append(value)
        elif name in {"type", "genre"} and value:
            types.append(value)
        elif name == "date" and value:
            dates.append((element.attrib.get("{http://www.idpf.org/2007/opf}event", ""), value))
    genre_words = {"roman", "novel", "fiction", "thriller", "essai", "poésie", "poesie", "science-fiction"}
    result["genre"] = next(
        (word.strip(" ,;:") for value in types + subjects for word in value.split() if word.casefold().strip(" ,;:") in genre_words),
        types[0] if types else "",
    )
    result["publication_date"] = next((value for event, value in dates if event.casefold() == "publication"), dates[0][1] if dates else "")
    if "T" in result["publication_date"]:
        result["publication_date"] = result["publication_date"].split("T", 1)[0]
    # Certains EPUB ont inversé dc:title et dc:creator. Un créateur contenant
    # une année est presque toujours le titre d'une œuvre, tandis que le titre
    # de deux mots capitalisés correspond alors au nom de l'auteur.
    if re.search(r"\b\d{2,4}\b", result["author"]) and re.fullmatch(r"[A-ZÀ-ÖØ-Ý][\wÀ-ÖØ-öø-ÿ'’-]+\s+[A-ZÀ-ÖØ-Ý][\wÀ-ÖØ-öø-ÿ'’-]+", result["title"]):
        result["title"], result["author"] = result["author"], result["title"]
    raw_author = result["author"].strip()
    if "," in raw_author:
        family, given = (part.strip() for part in raw_author.split(",", 1))
        author_parts = given.split() + family.split()
    else:
        author_parts = raw_author.split()
        if len(author_parts) >= 2 and author_parts[0].casefold() not in COMMON_GIVEN_NAMES and author_parts[1].casefold() in COMMON_GIVEN_NAMES:
            author_parts = author_parts[1:] + author_parts[:1]
    result["author"] = " ".join(author_parts)
    if len(author_parts) >= 2:
        result["author_firstname"] = " ".join(author_parts[:-1])
        result["author_lastname"] = author_parts[-1]
    elif author_parts:
        result["author_lastname"] = author_parts[0]
    return result


def manifest_and_spine(package: ET.Element):
    manifest = {}
    for item in package.iter():
        if local_name(item.tag) == "item" and item.attrib.get("id"):
            manifest[item.attrib["id"]] = item.attrib
    spine = []
    for itemref in package.iter():
        if local_name(itemref.tag) == "itemref" and itemref.attrib.get("idref") in manifest:
            spine.append(manifest[itemref.attrib["idref"]])
    return manifest, spine


def zip_path(base: str, href: str) -> str:
    return posixpath.normpath(posixpath.join(posixpath.dirname(base), href))


def cover_path(package: ET.Element, manifest: dict[str, dict[str, str]], base: str) -> str | None:
    cover_id = None
    for meta in package.iter():
        if local_name(meta.tag) == "meta" and meta.attrib.get("name", "").lower() == "cover":
            cover_id = meta.attrib.get("content")
    candidates = []
    for item_id, attributes in manifest.items():
        if item_id == cover_id or "cover-image" in attributes.get("properties", ""):
            candidates.append(attributes)
    if not candidates:
        candidates = [attributes for attributes in manifest.values() if "cover" in attributes.get("href", "").lower()]
    return zip_path(base, candidates[0]["href"]) if candidates else None


def toc_entries(archive: zipfile.ZipFile, package: ET.Element, manifest: dict[str, dict[str, str]], opf_path: str) -> list[tuple[str, str]]:
    """Retourne les cibles et intitulés du sommaire, dans son ordre."""
    toc_item = next(
        (attrs for attrs in manifest.values() if attrs.get("media-type") == "application/x-dtbncx+xml"),
        None,
    )
    if toc_item is None:
        toc_item = next((attrs for attrs in manifest.values() if "nav" in attrs.get("properties", "").split()), None)
    if toc_item is None:
        return []
    toc_path = zip_path(opf_path, toc_item["href"])
    try:
        raw = archive.read(toc_path)
    except KeyError:
        return []
    entries = []
    if toc_item.get("media-type") == "application/x-dtbncx+xml":
        root = ET.fromstring(raw)
        for navpoint in root.iter():
            if local_name(navpoint.tag) != "navpoint":
                continue
            src = next((child.attrib.get("src") for child in navpoint if local_name(child.tag) == "content"), "")
            label_node = next((child for child in navpoint if local_name(child.tag) == "navlabel"), None)
            label = text_value(label_node)
            if not src:
                continue
            target = zip_path(toc_path, src.split("#", 1)[0])
            if target not in [path for path, _ in entries]:
                entries.append((target, label))
    else:
        # EPUB 3 : navigation HTML, sans dépendance supplémentaire.
        for href, label in re.findall(r"<a\b[^>]*href\s*=\s*[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", raw.decode(TEXT_ENCODING, errors="replace"), re.I | re.S):
            target = zip_path(toc_path, unescape(href).split("#", 1)[0])
            label = " ".join(re.sub(r"<[^>]+>", " ", unescape(label)).split())
            if target not in [path for path, _ in entries]:
                entries.append((target, label))
    return entries


def significant_text(archive: zipfile.ZipFile, package: ET.Element, manifest, spine, title: str = "") -> str:
    # Le chemin OPF est injecté par extract_epub ; les hrefs sont déjà résolus ici.
    toc = toc_entries(archive, package, manifest, package.attrib.get("_path", ""))
    spine_paths = [attributes.get("_path", attributes.get("href", "")) for attributes in spine]
    front_positions = [
        index for index, (_, label) in enumerate(toc)
        if label.casefold().strip() == title.casefold().strip()
        or any(word in label.casefold() for word in TOC_FRONT_WORDS)
    ]
    # Après une préface/avant-propos, le prochain élément du sommaire est le
    # début narratif ; cela évite d'embarquer les pages liminaires.
    boundary_words = ("préface", "avant-propos", "avertissement", "mentions légales", "dédicace", "exergue")
    toc_start = None
    boundary_seen = False
    for index, (_, label) in enumerate(toc):
        lowered = label.casefold()
        if any(word in lowered for word in boundary_words):
            boundary_seen = True
            continue
        if boundary_seen and index not in front_positions:
            toc_start = index
            break
    if toc_start is None:
        toc_start = next((index for index in range(len(toc)) if index not in front_positions), 0)
    narrative_toc = toc[toc_start:]
    # Certains EPUB n'ont aucun chapitre dans le sommaire : uniquement les
    # pages liminaires et quelques rubriques éditoriales. Dans ce cas, le
    # récit commence au premier document après le dernier élément du sommaire.
    toc_only_front = not narrative_toc or all(label.casefold().strip() in TOC_FRONT_WORDS for _, label in narrative_toc)
    first_body_index = None
    if toc_only_front and toc:
        title_indexes = [spine_paths.index(target) for target, label in toc if target in spine_paths and label.casefold().strip() == title.casefold().strip()]
        if title_indexes:
            first_body_index = min(title_indexes)
        else:
            front_indexes = [spine_paths.index(target) for target, _ in toc if target in spine_paths]
            first_body_index = max(front_indexes, default=-1) + 1
        narrative_toc = []
    numbered_toc = [(target, label) for target, label in narrative_toc if NUMBERED_TOC.match(label.strip())]
    if numbered_toc:
        narrative_toc = numbered_toc
    toc_indexes = [spine_paths.index(target) for target, _ in narrative_toc if target in spine_paths]
    start_index = min(toc_indexes) if toc_indexes else (first_body_index if first_body_index is not None else 0)
    toc_labels = {target: label for target, label in narrative_toc if target in spine_paths}
    chunks = []
    for document_index, attributes in enumerate(spine):
        if document_index < start_index:
            continue
        href = attributes.get("_path", attributes.get("href", ""))
        lower = href.lower()
        if any(word in Path(lower).stem for word in SKIP_DOCUMENT_WORDS):
            continue
        try:
            parser = XHTMLText()
            parser.feed(archive.read(href).decode(TEXT_ENCODING, errors="replace"))
            text = parser.result()
        except KeyError:
            continue
        if text:
            label = toc_labels.get(href, "").strip()
            if label and document_index >= start_index:
                parsed = text.split("\n\n")
                document_stem = Path(href).stem.casefold()
                while parsed and parsed[0].casefold().strip() in {
                    document_stem,
                    document_stem.replace("_", " "),
                    title.casefold().strip(),
                }:
                    parsed.pop(0)
                if parsed and parsed[0].lstrip().startswith("#"):
                    parsed.pop(0)
                # Le sommaire peut déjà fusionner un numéro et son intitulé
                # (« 1. Evan »), alors que le XHTML les fournit séparément.
                if parsed and parsed[0].lstrip().startswith("#"):
                    heading_text = re.sub(r"^#+\s*", "", parsed[0]).strip().casefold()
                    if heading_text and heading_text in label.casefold():
                        parsed.pop(0)
                if parsed and re.fullmatch(r"#+\s*\d+[.)]?", parsed[0].strip()):
                    parsed.pop(0)
                label_parts = [part.strip().casefold() for part in re.split(r"\s+-\s+", label) if part.strip()]
                while parsed:
                    first = parsed[0].casefold().strip()
                    if first == title.casefold().strip() or first == label.casefold() or first in label_parts:
                        parsed.pop(0)
                    else:
                        break
                text = "\n\n".join([f"# {label}", *parsed])
            chunks.extend(text.split("\n\n"))
    title_key = title.casefold().strip()
    paragraphs = [paragraph for paragraph in chunks if paragraph.casefold().strip() != title_key]
    # Les EPUB structurés fournissent des titres de partie/chapitre ; ils
    # constituent le début fiable du texte, après les pages de garde et crédits.
    # On accepte aussi un titre éditorial (« Prologue », « Permis de tuer »…)
    # dès lors qu'il a été balisé comme titre dans le XHTML.
    if not toc:
        chapter_index = next((index for index, paragraph in enumerate(paragraphs) if CHAPTER_HEADING.match(paragraph.strip())), None)
        if chapter_index is None:
            chapter_index = next((index for index, paragraph in enumerate(paragraphs) if paragraph.lstrip().startswith("#")), None)
        if chapter_index is not None:
            paragraphs = paragraphs[chapter_index:]
    # Le titre du sommaire peut déjà être présent comme balise HTML : éviter
    # de conserver deux titres identiques consécutifs.
    compacted = []
    for paragraph in paragraphs:
        if not compacted or paragraph.strip() != compacted[-1].strip():
            compacted.append(paragraph)
    paragraphs = compacted
    # Une page de couverture peut être placée dans le premier XHTML narratif
    # (sans être signalée comme document « cover »). Elle ne fait pas partie
    # du texte : on retire cette section jusqu'au premier titre suivant.
    if paragraphs and paragraphs[0].casefold().strip() in {"# couverture", "# cover"}:
        next_heading = next((index for index, paragraph in enumerate(paragraphs[1:], 1) if paragraph.lstrip().startswith("#")), None)
        if next_heading is not None:
            paragraphs = paragraphs[next_heading:]
    if paragraphs and narrative_toc:
        # Le sommaire est l'autorité pour le premier titre : certains EPUB
        # placent dans le corps un titre interne (« Midi », par exemple).
        first_label = narrative_toc[0][1].strip()
        if first_label:
            first_heading = next((i for i, paragraph in enumerate(paragraphs) if paragraph.lstrip().startswith("#")), None)
            if first_heading is None:
                paragraphs.insert(0, f"# {first_label}")
            else:
                paragraphs[first_heading] = f"# {first_label}"
    # Dernier filet de sécurité : un intitulé de couverture réintroduit par
    # le sommaire ne doit jamais rester dans le texte narratif exporté.
    if paragraphs and paragraphs[0].casefold().strip() in {"# couverture", "# cover"}:
        next_heading = next((index for index, paragraph in enumerate(paragraphs[1:], 1) if paragraph.lstrip().startswith("#")), None)
        if next_heading is not None:
            paragraphs = paragraphs[next_heading:]
    # Sections éditoriales liminaires à exclure systématiquement, quel que
    # soit le nom des fichiers XHTML dans l'EPUB.
    preliminary = {"couverture", "cover", "auteur", "playlist", "copyright"}
    filtered, skipping = [], False
    for paragraph in paragraphs:
        heading = re.match(r"^#+\s*(.+?)\s*$", paragraph.strip())
        if heading:
            name = heading.group(1).casefold().strip(" .:-")
            if name in preliminary:
                skipping = True
                continue
            skipping = False
        if not skipping:
            filtered.append(paragraph)
    paragraphs = filtered
    # Uniformiser les apostrophes dès l'extraction : les EPUB mélangent
    # apostrophe ASCII, apostrophe typographique et variantes Unicode.
    # Cela garantit une tokenisation identique dans les analyses ultérieures.
    text = "\n\n".join(paragraphs).strip()
    return text.translate(str.maketrans({"’": "'", "‘": "'", "ʼ": "'", "＇": "'"}))


def yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def existing_metadata(path: Path) -> dict[str, str]:
    """Récupère les champs utiles avant de régénérer un Markdown existant."""
    if not path.exists():
        return {}
    text = path.read_text(encoding=TEXT_ENCODING, errors="replace")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    result = {}
    for line in text[4:end].splitlines():
        key, separator, value = line.partition(":")
        if separator:
            result[key.strip()] = value.strip().strip('"')
    return result


def register_publication_date(source_name: str, date: str) -> None:
    """Ajoute l'EPUB au registre sans écraser une clé déjà présente."""
    PUBLICATION_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing_keys = set()
    if PUBLICATION_FILE.exists():
        for line in PUBLICATION_FILE.read_text(encoding=TEXT_ENCODING).splitlines():
            clean = line.split("#", 1)[0].strip()
            if ":" in clean:
                existing_keys.add(clean.split(":", 1)[0].strip().strip("\"'"))
    if source_name in existing_keys:
        return
    year_match = re.match(r"^(\d{4})", date or "")
    year = year_match.group(1) if year_match else ""
    with PUBLICATION_FILE.open("a", encoding=TEXT_ENCODING) as handle:
        if PUBLICATION_FILE.stat().st_size:
            handle.write("\n")
        handle.write(f"{source_name}: {{date: {yaml_quote(year)}}}\n")


def organize_publication_file() -> None:
    """Regroupe les entrées par auteur et les trie chronologiquement."""
    if not PUBLICATION_FILE.exists():
        return
    lines = PUBLICATION_FILE.read_text(encoding=TEXT_ENCODING).splitlines()
    comments = [line for line in lines if not line.strip() or line.lstrip().startswith("#")]
    entries = []
    for line in lines:
        clean = line.split("#", 1)[0].strip()
        if not clean or ":" not in clean:
            continue
        key, raw_value = clean.split(":", 1)
        key = key.strip().strip("\"'")
        md = EPUB_DIR / Path(key).with_suffix(".md").name
        metadata = existing_metadata(md)
        author = metadata.get("author", "").strip()
        date_match = re.search(r"\bdate\s*:\s*[\"']([^\"']*)[\"']", raw_value)
        date = date_match.group(1) if date_match else ""
        year_match = re.match(r"^(\d{4})", date)
        if date_match and year_match:
            raw_value = raw_value[:date_match.start(1)] + year_match.group(1) + raw_value[date_match.end(1):]
            date = year_match.group(1)
        title_match = re.search(r"\btitle\s*:\s*[\"']([^\"']*)[\"']", raw_value)
        title = title_match.group(1) if title_match else key
        date_key = (date[:10] if re.match(r"^\d{4}(?:-\d{2}-\d{2})?", date) else "9999-99-99")
        entries.append((author.casefold(), date_key, title.casefold(), key, raw_value.strip()))
    if not entries:
        return
    entries.sort()
    output = []
    # Conserver les commentaires d'en-tête, sans reproduire les lignes vides.
    output.extend(line for line in comments if line.strip())
    previous_author = None
    for author, _, _, key, raw_value in entries:
        if previous_author is not None and author != previous_author:
            output.append("")
        output.append(f"{key}: {raw_value}")
        previous_author = author
    PUBLICATION_FILE.write_text("\n".join(output) + "\n", encoding=TEXT_ENCODING)


def web_slug(value: str) -> str:
    """Nom ASCII stable : exploitable dans une URL et lisible sur GitHub."""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.replace("&", " et ")
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return value or "livre"


def convert_cover(archive: zipfile.ZipFile, member: str, destination: Path) -> None:
    executable = next((candidate for candidate in ("magick", "convert") if shutil.which(candidate)), None)
    if executable is None:
        raise RuntimeError("ImageMagick (magick ou convert) est nécessaire pour produire l’AVIF")
    destination.parent.mkdir(parents=True, exist_ok=True)
    suffix = Path(member).suffix or ".img"
    with tempfile.NamedTemporaryFile(suffix=suffix) as temporary:
        temporary.write(archive.read(member))
        temporary.flush()
        command = [executable, temporary.name, "-strip", "-quality", "70", str(destination)]
        completed = subprocess.run(command, capture_output=True, text=True)
        # Certains EPUB fournissent une couverture SVG sans width/height.
        # ImageMagick ne peut alors pas déterminer la taille du canevas ; on
        # lui donne une taille de rasterisation raisonnable pour la seconde
        # tentative, sans modifier le fichier original.
        if completed.returncode and suffix.lower() == ".svg":
            command = [executable, "-background", "white", "-size", "1200x1800", f"svg:{temporary.name}", "-strip", "-quality", "70", str(destination)]
            completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or f"conversion impossible pour {member}")


def extract_epub(source: Path) -> tuple[Path, None]:
    with zipfile.ZipFile(source) as archive:
        opf_path, package = package_root(archive)
        package.attrib["_path"] = opf_path
        info = metadata(package)
        manifest, spine = manifest_and_spine(package)
        for attributes in spine:
            attributes["_path"] = str(Path(opf_path).parent / attributes["href"]).replace("\\", "/")
        text = significant_text(archive, package, manifest, spine, info["title"])
        if len(text) < EPUB_ANALYSIS_WINDOW_SIZE:
            raise ShortEpubError(source, len(text), EPUB_ANALYSIS_WINDOW_SIZE)
        date = info.get("publication_date", "")
        year = int(date[:4]) if re.match(r"^\d{4}", date) else 0
        if not date or year < 1500 or year > 2100:
            info["publication_date"] = ""
            match = COPYRIGHT_YEAR.search(text)
            if match:
                info["publication_date"] = match.group(1)
        output_stem = web_slug(source.stem)
        output_md = source.parent / f"{output_stem}.md"
        previous = existing_metadata(output_md)
        # Certains EPUB ne déclarent pas correctement leur créateur. Dans ce
        # cas, une régénération ne doit pas effacer l'auteur déjà validé dans
        # le Markdown.
        if not info["author"] and previous.get("author"):
            for key in ("author", "author_firstname", "author_lastname"):
                if previous.get(key):
                    info[key] = previous[key]
        front_matter = ["---"]
        for key in ("title", "author", "author_firstname", "author_lastname", "publisher", "genre", "publication_date"):
            front_matter.append(f"{key}: {yaml_quote(info[key])}")
        front_matter.append(f"size: {len(text)}")
        front_matter.append("source: " + yaml_quote(f"{output_stem}.epub"))
        front_matter.append("---")
        output_md.write_text("\n".join(front_matter) + "\n\n" + text + "\n", encoding=TEXT_ENCODING)
        register_publication_date(f"{output_stem}.epub", info.get("publication_date", ""))
    return output_md, None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Extrait les EPUB en Markdown")
    parser.add_argument("epubs", nargs="*", type=Path, help="EPUB à traiter ; sans argument, tous les EPUB de _epub")
    args = parser.parse_args(argv)
    sources = args.epubs or sorted(EPUB_DIR.glob("*.epub"))
    if not sources:
        parser.error(f"aucun EPUB dans {EPUB_DIR}")
    normalized_sources = []
    for source in sources:
        target = source.parent / f"{web_slug(source.stem)}.epub"
        if source != target and source.exists() and not target.exists():
            source.rename(target)
            source = target
        normalized_sources.append(source)
    skipped = False
    EPUB_HASH_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        hash_cache = json.loads(EPUB_HASH_CACHE_FILE.read_text(encoding=TEXT_ENCODING))
    except (FileNotFoundError, json.JSONDecodeError):
        hash_cache = {}
    for source in normalized_sources:
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        output_md = source.parent / f"{web_slug(source.stem)}.md"
        if output_md.exists() and hash_cache.get(source.name) == digest:
            print(f"Déjà extrait : {source.name} -> {output_md.name}", flush=True)
            continue
        try:
            markdown, _ = extract_epub(source)
        except ShortEpubError as error:
            skipped = True
            print(f"ALERTE : {error}", flush=True)
            continue
        print(f"Extrait : {source.name} -> {markdown.name}", flush=True)
        hash_cache[source.name] = digest
    EPUB_HASH_CACHE_FILE.write_text(json.dumps(hash_cache, ensure_ascii=False, indent=2) + "\n", encoding=TEXT_ENCODING)
    organize_publication_file()
    # Une source unique en échec doit interrompre epubs.sh avant toute analyse
    # d'un ancien Markdown portant le même nom. En traitement global, les
    # autres EPUB sont tout de même extraits et synchronisés.
    return 1 if skipped and len(normalized_sources) == 1 else 0


if __name__ == "__main__":
    raise SystemExit(main())
