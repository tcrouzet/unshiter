"""Exporte la base SQLite vers les données statiques du site web."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

from .config import EPUB_DATABASE, SITE_CONFIG_FILE, TEXT_ENCODING, WEB_DATA_FILE


def site_config() -> dict[str, str]:
    values = {"name": "Site Unshiter", "author": "Thierry Crouzet", "author_url": "https://tcrouzet.com", "description": "", "coverage_help": "Surface sur le graphique radar."}
    if SITE_CONFIG_FILE.exists():
        for line in SITE_CONFIG_FILE.read_text(encoding=TEXT_ENCODING).splitlines():
            key, separator, value = line.partition(":")
            if separator and key.strip() in values:
                values[key.strip()] = value.strip().strip('"\'')
    return values


def export_json() -> int:
    WEB_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not EPUB_DATABASE.exists():
        payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "site": site_config(), "books": []}
    else:
        with sqlite3.connect(EPUB_DATABASE) as db:
            db.row_factory = sqlite3.Row
            books = []
            for book in db.execute("SELECT id,path,title,author,publisher,publication_date,size,sha256 FROM books ORDER BY title COLLATE NOCASE"):
                analyses = []
                for row in db.execute("SELECT window_index,char_start,char_end,char_count,stats_json FROM analyses WHERE book_id=? ORDER BY window_index", (book["id"],)):
                    analyses.append({
                        "window": row["window_index"], "start": row["char_start"], "end": row["char_end"],
                        "chars": row["char_count"], "stats": json.loads(row["stats_json"]),
                    })
                books.append({
                    "id": book["id"], "filename": Path(book["path"]).name, "title": book["title"],
                    "author": book["author"], "publisher": book["publisher"],
                    "publication_date": book["publication_date"], "size": book["size"],
                    "sha256": book["sha256"], "analyses": analyses,
                })
        payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "site": site_config(), "books": books}
    WEB_DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding=TEXT_ENCODING)
    return len(payload["books"])


if __name__ == "__main__":
    print(f"{export_json()} livres exportés vers {WEB_DATA_FILE}")
