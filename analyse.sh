#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON="$PROJECT_ROOT/venv/bin/python"
if [ ! -x "$PYTHON" ]; then PYTHON=python3; fi

if [ "$#" -ne 2 ]; then
  echo "Usage : ./analyse.sh chemin/source.md nom_metric" >&2
  exit 2
fi

case "$1" in
  /*) SOURCE=$1 ;;
  *) SOURCE=$PWD/$1 ;;
esac
cd "$PROJECT_ROOT"

OUTPUT=$(PYTHONPATH="$PROJECT_ROOT/script" "$PYTHON" -m detector.analyse "$SOURCE" "$2")
printf '%s\n' "$OUTPUT"

if command -v open >/dev/null 2>&1; then
  open "$OUTPUT"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$OUTPUT"
fi
