"""Index local du lexique FEEL (LIRMM)."""
import csv, sqlite3
from functools import lru_cache
from .config import FEEL_ARCHIVE, FEEL_INDEX

def ensure_index():
    if FEEL_INDEX.exists(): return
    if not FEEL_ARCHIVE.exists(): return
    FEEL_INDEX.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(FEEL_INDEX) as db:
        db.execute('create table emotion (lemma text, tag text, primary key (lemma,tag))')
        with FEEL_ARCHIVE.open(encoding='utf-8-sig', newline='') as f:
            reader=csv.DictReader(f, delimiter=';')
            for row in reader:
                word=(row.get('word') or '').strip().casefold()
                if not word: continue
                tags=[k for k,v in row.items() if k not in {'id','word','polarity'} and str(v).strip() not in {'','0'}]
                if not tags: tags=[row.get('polarity','')]
                for tag in tags:
                    if tag: db.execute('insert or ignore into emotion values (?,?)',(word,tag))
        db.commit()

@lru_cache(maxsize=4096)
def emotion_map(lemmas: tuple[str,...]) -> dict[str,set[str]]:
    ensure_index()
    if not FEEL_INDEX.exists(): return {}
    vals=tuple(set(lemmas))
    if not vals: return {}
    with sqlite3.connect(FEEL_INDEX) as db:
        rows=db.execute('select lemma,tag from emotion where lemma in ({})'.format(','.join('?'*len(vals))),vals).fetchall()
    out={}
    for lemma,tag in rows: out.setdefault(lemma,set()).add(tag)
    return out
