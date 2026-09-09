#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$PROJECT_ROOT"
PYTHON="$PROJECT_ROOT/venv/bin/python"
if [ ! -x "$PYTHON" ]; then PYTHON=python3; fi

# Une seule génération peut écrire dans la base SQLite partagée à la fois.
# mkdir est atomique et évite une longue trace sqlite "database is locked".
LOCK_DIR="$PROJECT_ROOT/_temp/epubs.lock"
mkdir -p "$PROJECT_ROOT/_temp"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "Une autre commande epubs.sh utilise déjà la base. Attendez sa fin puis relancez." >&2
  exit 3
fi

cleanup_lock() { rmdir "$LOCK_DIR" 2>/dev/null || true; }
trap cleanup_lock EXIT HUP INT TERM

reset_all=0
if [ "$#" -eq 1 ] && [ "$1" = "--reset" ]; then
  reset_all=1
  echo "Réinitialisation complète de la base SQLite..."
  PYTHONPATH=script "$PYTHON" -m detector.epub_database --reset-only
  shift
elif [ "$#" -gt 0 ] && [ "$1" = "--reset" ]; then
  echo "Usage : ./epubs.sh [--reset|corpus|fichier.epub|fichier.md]" >&2
  exit 2
fi

process_corpus() {
  corpus_id=$1
  corpus_dir="$PROJECT_ROOT/corpus/$corpus_id"
  if [ ! -d "$corpus_dir" ]; then
    echo "Corpus introuvable : $corpus_id" >&2
    return 2
  fi
  echo "=== Corpus : $corpus_id ==="
  if find "$corpus_dir" -type f -name '*.epub' -print -quit | grep -q .; then
    echo "[1/3] Extraction des EPUB en Markdown..."
    UNSHITER_CORPUS="$corpus_id" "$PYTHON" script/epub-extraction.py
  else
    echo "[1/3] Aucun EPUB à extraire."
  fi
  echo "[2/3] Recherche des dates de publication manquantes..."
  UNSHITER_CORPUS="$corpus_id" "$PYTHON" script/publication-dates.py || true
  echo "[3/3] Analyse et mise à jour de la base..."
  PYTHONPATH=script UNSHITER_CORPUS="$corpus_id" "$PYTHON" -m detector.epub_database --corpus "$corpus_id"
}

if [ "$#" -eq 0 ]; then
  found=0
  for corpus_dir in "$PROJECT_ROOT"/corpus/*; do
    [ -d "$corpus_dir" ] || continue
    found=1
    process_corpus "$(basename "$corpus_dir")"
  done
  if [ "$found" -eq 0 ]; then
    echo "Aucun corpus dans $PROJECT_ROOT/corpus" >&2
    exit 2
  fi
elif [ "$#" -eq 1 ] && [ -d "$PROJECT_ROOT/corpus/$1" ]; then
  process_corpus "$1"
else
  if [ "$#" -ne 1 ]; then
    echo "Usage : ./epubs.sh [--reset|corpus|fichier.epub|fichier.md]" >&2
    exit 2
  fi
  case "$1" in
    "$PROJECT_ROOT"/corpus/*|corpus/*)
      relative=${1#"$PROJECT_ROOT"/corpus/}
      relative=${relative#corpus/}
      corpus_id=${relative%%/*}
      ;;
    *) corpus_id=${UNSHITER_CORPUS:-crouzet} ;;
  esac
  echo "[1/1] Préparation de la source..."
  case "$1" in
    *.epub)
      extracted=$(UNSHITER_CORPUS="$corpus_id" "$PYTHON" script/epub-extraction.py "$1")
      printf '%s\n' "$extracted"
      # L'extracteur affiche un message humain ; le chemin de sortie est
      # déterministe à partir de l'EPUB normalisé.
      file="${1%.epub}.md"
      ;;
    *.md) file="$1" ;;
    *.avif) file="${1%.avif}.md" ;;
    *) echo "Fichier attendu : .epub, .md ou .avif" >&2; exit 2 ;;
  esac
  if [ ! -f "$file" ]; then
    echo "Markdown introuvable : $file" >&2
    exit 1
  fi
  echo "Recherche des dates de publication manquantes..."
  UNSHITER_CORPUS="$corpus_id" "$PYTHON" script/publication-dates.py || true
  PYTHONPATH=script UNSHITER_CORPUS="$corpus_id" "$PYTHON" -m detector.epub_database --corpus "$corpus_id" "$file"
fi

if [ "$reset_all" -eq 1 ]; then
  echo "Génération complète des données web..."
  "$PROJECT_ROOT/web.sh"
fi
