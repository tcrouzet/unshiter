#!/usr/bin/env bash
# Analyse le fichier Markdown défini dans script/burstiness/config.py et
# ouvre le résultat dans le navigateur. Aucun paramètre : tout se règle
# dans config.py.

set -euo pipefail

cd "$(dirname "$0")"

OUTPUT="$(python3 -m script.burstiness.cli)"

if command -v open >/dev/null 2>&1; then
  open "$OUTPUT"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$OUTPUT"
else
  echo "Ouvrez manuellement : $OUTPUT"
fi
