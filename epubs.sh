#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$PROJECT_ROOT"
PYTHON="$PROJECT_ROOT/venv/bin/python"
if [ ! -x "$PYTHON" ]; then PYTHON=python3; fi

if [ "$#" -eq 0 ]; then
  echo "[1/3] Extraction des EPUB en Markdown..."
  "$PYTHON" script/epub-extraction.py
  echo "[2/3] Recherche des dates de publication manquantes..."
  "$PYTHON" script/publication-dates.py || true
  echo "[3/3] Analyse et mise à jour de la base..."
  PYTHONPATH=script "$PYTHON" -m detector.epub_database
else
  echo "[1/1] Préparation de la source..."
  case "$1" in
    *.epub)
      extracted=$("$PYTHON" script/epub-extraction.py "$1")
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
  "$PYTHON" script/publication-dates.py || true
  PYTHONPATH=script "$PYTHON" -m detector.epub_database "$file"
fi
