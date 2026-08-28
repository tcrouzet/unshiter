"""Accès optionnel aux fréquences lexicales Lexique383."""
from functools import lru_cache
import csv
import sqlite3

from .config import LEXIQUE_ARCHIVE, LEXIQUE_INDEX


def _index_ready() -> bool:
    if not LEXIQUE_INDEX.is_file():
        return False
    try:
        with sqlite3.connect(LEXIQUE_INDEX) as db:
            db.execute("select 1 from lexicon limit 1")
        return True
    except sqlite3.Error:
        return False


def ensure_index() -> None:
    if _index_ready() or not LEXIQUE_ARCHIVE.is_file():
        return
    LEXIQUE_INDEX.parent.mkdir(parents=True, exist_ok=True)
    tmp = LEXIQUE_INDEX.with_suffix('.building')
    if tmp.exists(): tmp.unlink()
    with sqlite3.connect(tmp) as db:
        db.execute('create table lexicon (lemma text primary key, frequency real)')
        with LEXIQUE_ARCHIVE.open(encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle, delimiter='\t')
            for row in reader:
                lemma = (row.get('lemme') or row.get('Lemma') or '').strip().casefold()
                raw = (row.get('freqlivres') or row.get('FreqLivres') or '').replace(',', '.')
                try: frequency = float(raw)
                except ValueError: continue
                if lemma: db.execute('insert or replace into lexicon values (?,?)', (lemma, frequency))
        db.commit()
    tmp.replace(LEXIQUE_INDEX)


@lru_cache(maxsize=4096)
def frequency_map(lemmas: tuple[str, ...]) -> dict[str, float]:
    ensure_index()
    if not _index_ready():
        return {}
    with sqlite3.connect(LEXIQUE_INDEX) as db:
        rows = db.execute('select lemma, frequency from lexicon where lemma in ({})'.format(','.join('?' for _ in set(lemmas))), tuple(set(lemmas))).fetchall()
    return dict(rows)
