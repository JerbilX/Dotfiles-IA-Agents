#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REF_DIR="$SCRIPT_DIR/../references"

DOCS_FILE="$REF_DIR/ESOUIDocumentation.txt"
DOCS_URL="https://raw.githubusercontent.com/esoui/esoui/live/ESOUIDocumentation.txt"

STRINGS_FILE="$REF_DIR/localizegeneratedstrings.lua"
STRINGS_URL="https://raw.githubusercontent.com/esoui/esoui/live/esoui/ingamelocalization/localizegeneratedstrings.lua"

echo "Descargando la última versión de ESOUIDocumentation.txt..."
curl -sSL "$DOCS_URL" -o "$DOCS_FILE"
echo "Actualizado: $DOCS_FILE"
head -n 2 "$DOCS_FILE"

echo "Descargando la última versión de localizegeneratedstrings.lua..."
curl -sSL "$STRINGS_URL" -o "$STRINGS_FILE"
echo "Actualizado: $STRINGS_FILE"
echo "Sincronización completada exitosamente."
