#!/bin/sh
set -eu
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$PROJECT_ROOT"
PYTHON="$PROJECT_ROOT/venv/bin/python"
if [ ! -x "$PYTHON" ]; then PYTHON=python3; fi
PYTHONPATH=script "$PYTHON" -m detector.web_export
cp assets/style-interpretation-prompt.md web/style-interpretation-prompt.md
VERSION=$(date +%Y%m%d%H%M%S%N)
VERSION="$VERSION" perl -pi -e 's/__WEB_VERSION__/$ENV{VERSION}/g; s/(style\.css\?v=)[^"]+/${1}$ENV{VERSION}/g; s/(app\.js\?v=)[^"]+/${1}$ENV{VERSION}/g; s/(data\.json\?v=)[^"\)]+/${1}$ENV{VERSION}/g; s/(favicon\.svg\?v=)[^"]+/${1}$ENV{VERSION}/g; s/(social-preview\.png\?v=)[^"]+/${1}$ENV{VERSION}/g' web/index.html web/app.js
