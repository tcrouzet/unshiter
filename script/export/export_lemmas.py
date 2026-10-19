"""Exporte un dictionnaire mot -> lemme (Morphalou) et la liste des mots-outils
en JSON, pour une consommation côté JavaScript (plugin Obsidian).

À placer dans unshiter/script/export/export_lemmas.py puis lancer depuis la
racine du projet (pas besoin de -m ni de PYTHONPATH, le script s'ajoute
lui-même à sys.path) :

    venv/bin/python script/export/export_lemmas.py

Produit :
    obsidian-plugin/data/lexicon.json            (mot -> lemme, mot != lemme uniquement)
    obsidian-plugin/data/function-words.json     (liste à plat des mots-outils)
    obsidian-plugin/data/epistemic-hedging.json  (locutions de prudence épistémique)
    obsidian-plugin/data/stereotypes.json        (motifs de stéréotypes, en lemmes ;
                                                   nécessite spaCy + fr_core_news_lg,
                                                   absent sinon sans bloquer le reste)
"""

from __future__ import annotations

import csv
import io
import json
import sqlite3
import sys
import zipfile
from pathlib import Path

# Ce script vit dans script/export/, mais importe le package detector/ qui
# vit dans script/. On ajoute donc script/ à sys.path avant les imports, ce
# qui évite l'erreur "attempted relative import with no known parent
# package" qu'on aurait avec `from .config import ...` en exécution directe.
_SCRIPT_DIR = Path(__file__).resolve().parents[1]  # .../unshiter/script
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from detector.config import (  # noqa: E402
    EPISTEMIC_HEDGING_FILE,
    FUNCTION_WORDS_FILE,
    MORPHALOU_ARCHIVE,
    MORPHALOU_CSV_MEMBER,
    MORPHALOU_INDEX,
    PROJECT_ROOT,
    STEREOTYPES_FILE,
    TEXT_ENCODING,
)
from detector.morphalou import ensure_index, normalize_form  # noqa: E402

OUTPUT_DIR = PROJECT_ROOT / "obsidian-plugin" / "data"


def _best_form_lemma_map() -> dict[str, str]:
    """Aplati Morphalou en form -> lemme, en choisissant le MEILLEUR candidat
    pour chaque forme ambiguë — sans jamais fusionner de groupes entiers.

    Pour une forme homographe ("tremble" = nom "tremble" OU verbe
    "trembler"), on préfère la lecture VERBE (c'est elle qui intéresse un
    détecteur de répétitions d'actions dans un texte narratif) ; à défaut de
    verbe candidat, le lemme le plus court (choix déterministe).

    Une première version fusionnait des GROUPES ENTIERS de lemmes dès qu'une
    seule forme était ambiguë (union-find). Ça a produit un faux positif :
    "durent" est ambigu entre "durer" (ils durent, présent) et "devoir" (ils
    durent attendre, passé simple) ; fusionner les groupes entiers entraînait
    alors TOUTES les formes de durer ET de devoir dans un seul groupe
    (durant, devant, dois, doit...), rendant "devant" et "durant"
    indiscernables l'un de l'autre alors qu'ils ne sont eux-mêmes pas
    ambigus. Ici, seule la forme ambiguë elle-même est tranchée ; toutes les
    autres formes de chaque lemme restent correctement séparées.
    """
    form_candidates: dict[str, dict[str, str]] = {}  # form -> {lemme: catégorie}
    current_lemma = ""
    current_category = ""
    with zipfile.ZipFile(MORPHALOU_ARCHIVE) as archive:
        with archive.open(MORPHALOU_CSV_MEMBER) as binary:
            reader = csv.reader(io.TextIOWrapper(binary, encoding="utf-8-sig", newline=""), delimiter=";")
            data_started = False
            for row in reader:
                if not data_started:
                    data_started = len(row) > 9 and row[0] == "GRAPHIE" and row[9] == "GRAPHIE"
                    continue
                if len(row) <= 9:
                    continue
                if row[0].strip():
                    current_lemma = normalize_form(row[0])
                    current_category = row[2].strip().lower()
                form = normalize_form(row[9])
                if not current_lemma or not form:
                    continue
                form_candidates.setdefault(form, {})[current_lemma] = current_category

    mapping: dict[str, str] = {}
    for form, candidates in form_candidates.items():
        if len(form) < 2:
            continue
        if len(candidates) == 1:
            lemma = next(iter(candidates))
        else:
            verb_lemmas = sorted(
                (lemma for lemma, category in candidates.items() if category.startswith("verbe")),
                key=lambda lemma: (len(lemma), lemma),
            )
            lemma = verb_lemmas[0] if verb_lemmas else min(candidates, key=lambda lemma: (len(lemma), lemma))
        if form != lemma:
            mapping[form] = lemma
    return mapping


def export_lemma_map(mapping: dict[str, str]) -> None:
    """Exporte le dict form -> lemme (voir _best_form_lemma_map)."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    destination = OUTPUT_DIR / "lexicon.json"
    destination.write_text(
        json.dumps(mapping, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"{len(mapping)} formes exportées -> {destination}")


def _resolve_function_words() -> set[str]:
    """Résout function-words.txt en une liste à plat de formes concrètes.

    Le fichier distingue quatre types de lignes (confirmé en lisant le
    fichier réel, pas deviné) :
    - mot:X       -> la forme X elle-même
    - lemme:X     -> toutes les formes de Morphalou dont le lemme est X
                     (ex. lemme:être -> suis, es, est, sommes, étais...)
    - catégorie:X -> toutes les formes de Morphalou dont la catégorie
                     commence par X (ex. catégorie:déterminant -> matche
                     "déterminant possessif", "déterminant démonstratif"...)
    - garder:X    -> exception, retire X du résultat final même s'il a été
                     ajouté par une des règles ci-dessus

    Fonction partagée entre export_function_words() (export JSON direct pour
    le plugin) et export_stereotype_patterns() (filtrage des motifs) : les
    deux DOIVENT utiliser exactement la même liste, sinon le motif exporté et
    le texte filtré côté JS peuvent diverger sur un mot ambigu ("si" peut
    être conjonction ou adverbe selon le contexte) et ne plus jamais matcher.
    """
    ensure_index()
    words: set[str] = set()
    lemmas: set[str] = set()
    categories: set[str] = set()
    kept: set[str] = set()

    for raw_line in FUNCTION_WORDS_FILE.read_text(encoding=TEXT_ENCODING).splitlines():
        line = raw_line.strip().lower()
        if not line or line.startswith("#"):
            continue
        kind, separator, value = line.partition(":")
        if not separator or not value.strip():
            continue
        value = value.strip().replace("’", "'")
        if kind == "mot":
            words.add(value)
        elif kind == "lemme":
            lemmas.add(value)
        elif kind in {"catégorie", "categorie"}:
            categories.add(value)
        elif kind == "garder":
            kept.add(value)

    with sqlite3.connect(MORPHALOU_INDEX) as connection:
        if lemmas:
            placeholders = ",".join("?" for _ in lemmas)
            rows = connection.execute(
                f"SELECT form FROM lexicon WHERE lower(lemma) IN ({placeholders})",
                tuple(lemmas),
            )
            words.update(form for (form,) in rows)
        if categories:
            rows = connection.execute("SELECT form, category FROM lexicon")
            for form, category in rows:
                normalized_category = (category or "").strip().lower()
                if any(normalized_category.startswith(prefix) for prefix in categories):
                    words.add(form)

    words -= kept
    # Les lemmes eux-mêmes (pas seulement les formes fléchies) doivent aussi
    # être exclus : export_stereotype_patterns() compare des LEMMES, pas des
    # formes de surface, et un lemme comme "être" n'est pas forcément déjà
    # dans `words` (certaines formes fléchies de être peuvent elles-mêmes
    # servir de lemme à d'autres mots par coïncidence, mais rien ne garantit
    # que "être" lui-même y figure).
    words.update(lemmas)
    return words


def export_function_words() -> None:
    """Exporte la liste à plat des mots-outils (voir _resolve_function_words)."""
    words = _resolve_function_words()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    destination = OUTPUT_DIR / "function-words.json"
    destination.write_text(json.dumps(sorted(words), ensure_ascii=False), encoding="utf-8")
    print(f"{len(words)} mots-outils exportés -> {destination}")


def export_epistemic_hedging() -> None:
    """Aplati epistemic-hedging.txt (une locution par ligne) en liste JSON."""
    phrases = [
        line.strip()
        for line in EPISTEMIC_HEDGING_FILE.read_text(encoding=TEXT_ENCODING).splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    destination = OUTPUT_DIR / "epistemic-hedging.json"
    destination.write_text(json.dumps(phrases, ensure_ascii=False), encoding="utf-8")
    print(f"{len(phrases)} locutions d'hedging exportées -> {destination}")


def export_stereotype_patterns(merged_lemma_map: dict[str, str]) -> None:
    """Lemmatise assets/dictionnaires/stereotypes.txt via spaCy (une fois, hors
    ligne) et exporte une liste de motifs (listes de lemmes). Le plugin JS n'a
    pas besoin de spaCy : il compare simplement ses propres lemmes (résolus
    via lexicon.json) à ces séquences, mot par mot, dans l'ordre.

    Ces expressions ("le cœur s'emballer", "serrer les poings") sont écrites
    à l'infinitif mais apparaissent conjuguées dans un texte réel ("son cœur
    s'emballa") : une correspondance littérale ne trouverait donc rien, d'où
    le passage par la lemmatisation, contrairement à export_epistemic_hedging
    dont les locutions sont déjà figées telles qu'elles apparaissent.

    `merged_lemma_map` (form -> lemme, voir _best_form_lemma_map) est réutilisé
    ici pour re-canoniser le lemme que spaCy attribue à chaque mot du motif,
    pour que motif et texte analysé parlent le même vocabulaire (même choix
    pour les formes ambiguës comme "tremble").
    """
    from detector.syntax_depth import _pipeline  # import tardif : spaCy est lourd

    pipeline = _pipeline()
    if pipeline is None:
        print(
            "spaCy indisponible (modèle fr_core_news_lg non installé) : "
            "stereotypes.json non généré, mode Stéréotypes restera vide côté plugin."
        )
        return

    lines = [
        line.split("#", 1)[0].strip()
        for line in STEREOTYPES_FILE.read_text(encoding=TEXT_ENCODING).splitlines()
    ]
    lines = [line for line in lines if line]

    # On filtre le motif avec EXACTEMENT la même liste de mots-outils que
    # celle exportée vers function-words.json et utilisée par le plugin JS
    # pour filtrer le texte analysé (voir _resolve_function_words). Utiliser
    # les étiquettes grammaticales spaCy (DET/ADP/PRON...) ici donnait un
    # filtrage différent de celui du JS sur les mots ambigus selon le
    # contexte ("si" conjonction ou adverbe, etc.), ce qui désynchronisait
    # motif et texte et empêchait toute correspondance, même exacte.
    function_words = _resolve_function_words()

    seen: set[tuple[str, ...]] = set()
    patterns: list[list[str]] = []
    for doc in pipeline.pipe(lines):
        lemmas = tuple(
            merged_lemma_map.get(token.lemma_.casefold(), token.lemma_.casefold())
            for token in doc
            if not token.is_space
            and not token.is_punct
            and token.text.casefold() not in function_words
            and token.lemma_.casefold() not in function_words
        )
        if lemmas and lemmas not in seen:
            seen.add(lemmas)
            patterns.append(list(lemmas))

    # Motifs les plus longs d'abord : évite qu'un motif court masque une
    # correspondance plus longue qui le contiendrait (le JS retrie de toute
    # façon, mais autant livrer un fichier déjà cohérent).
    patterns.sort(key=len, reverse=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    destination = OUTPUT_DIR / "stereotypes.json"
    destination.write_text(json.dumps(patterns, ensure_ascii=False), encoding="utf-8")
    print(f"{len(patterns)} motifs de stéréotypes exportés -> {destination}")


if __name__ == "__main__":
    # Calculé une seule fois, réutilisé par les répétitions ET les
    # stéréotypes : les deux doivent parler exactement le même vocabulaire,
    # sans quoi un motif de stéréotype pourrait utiliser un lemme que le
    # texte analysé ne produira jamais pour une forme ambiguë.
    merged_lemma_map = _best_form_lemma_map()
    export_lemma_map(merged_lemma_map)
    export_function_words()
    export_epistemic_hedging()
    export_stereotype_patterns(merged_lemma_map)
