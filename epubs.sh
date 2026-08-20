#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$PROJECT_ROOT"
PYTHON="$PROJECT_ROOT/venv/bin/python"
if [ ! -x "$PYTHON" ]; then PYTHON=python3; fi

if [ "$#" -eq 0 ]; then
  "$PYTHON" script/epub-extraction.py
  PYTHONPATH=script "$PYTHON" -m detector.epub_database
else
  case "$1" in
    *.epub)
      extracted=$("$PYTHON" script/epub-extraction.py "$1")
      printf '%s\n' "$extracted"
      file=$(printf '%s\n' "$extracted" | sed -n '1p')
      ;;
    *.md) file="$1" ;;
    *.avif) file="${1%.avif}.md" ;;
    *) echo "Fichier attendu : .epub, .md ou .avif" >&2; exit 2 ;;
  esac
  if [ ! -f "$file" ]; then
    echo "Markdown introuvable : $file" >&2
    exit 1
  fi
  PYTHONPATH=script "$PYTHON" -m detector.epub_database "$file"
fi
