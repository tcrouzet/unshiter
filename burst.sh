#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON="$PROJECT_ROOT/venv/bin/python"
if [ ! -x "$PYTHON" ]; then PYTHON=python3; fi

if [ "$#" -ne 1 ]; then
  echo "Usage : ./burst.sh chemin/source.md" >&2
  exit 2
fi

case "$1" in
  /*) SOURCE=$1 ;;
  *) SOURCE=$PWD/$1 ;;
esac
cd "$PROJECT_ROOT"

OUTPUT=$("$PYTHON" -m script.burstiness.cli "$SOURCE")
printf '%s\n' "$OUTPUT"

if command -v open >/dev/null 2>&1; then
  open "$OUTPUT"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$OUTPUT"
else
  echo "Ouvrez manuellement : $OUTPUT"
fi
