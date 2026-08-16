#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON="$PROJECT_DIR/venv/bin/python"
if [ ! -x "$PYTHON" ]; then
    PYTHON=python3
fi
PYTHONPATH="$PROJECT_DIR/script${PYTHONPATH:+:$PYTHONPATH}" exec "$PYTHON" -m detector.stats "$@"
