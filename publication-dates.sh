#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PYTHON="$(pwd)/venv/bin/python"
[ -x "$PYTHON" ] || PYTHON=python3
exec env PYTHONPATH="$(pwd)/script${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON" script/publication-dates.py "$@"
