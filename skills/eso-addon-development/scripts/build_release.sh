#!/bin/bash
# Script centralizado para empaquetar addons de ESO e inyectar metadatos en tiempo de build

if [ -z "$1" ]; then
  echo "Uso: $0 <ruta_al_directorio_del_addon>"
  exit 1
fi

ADDON_DIR=$(realpath "$1")
ADDON_NAME=$(basename "$ADDON_DIR")
MANIFEST_FILE="$ADDON_DIR/${ADDON_NAME}.txt"

if [ ! -f "$MANIFEST_FILE" ]; then
  echo "Error: No se encontró el manifiesto $MANIFEST_FILE"
  exit 1
fi

# Extraer versión del manifiesto
VERSION=$(grep -iE "^## Version:" "$MANIFEST_FILE" | awk '{print $3}' | tr -d '\r')

if [ -z "$VERSION" ]; then
  echo "Error: No se pudo extraer la versión del manifiesto. Asegúrate de que exista '## Version: X.Y.Z'."
  exit 1
fi

echo "Empaquetando $ADDON_NAME v$VERSION..."

# Crear directorio de build temporal
BUILD_DIR="/tmp/${ADDON_NAME}_build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/$ADDON_NAME"

# Copiar archivos ignorando git, tests y la carpeta dist
rsync -av --exclude='.git' --exclude='tests' --exclude='scripts' --exclude='dist' --exclude='*.zip' "$ADDON_DIR/" "$BUILD_DIR/$ADDON_NAME/" > /dev/null

# Inyectar versión en todos los archivos Lua
find "$BUILD_DIR/$ADDON_NAME" -name "*.lua" -type f -exec sed -i "s/@BUILD_VERSION@/$VERSION/g" {} +

# Crear archivo ZIP final
DIST_DIR="$ADDON_DIR/dist"
mkdir -p "$DIST_DIR"
ZIP_FILE="$DIST_DIR/${ADDON_NAME}-${VERSION}.zip"

cd "$BUILD_DIR" || exit
zip -r "$ZIP_FILE" "$ADDON_NAME" > /dev/null

echo "Artefacto generado exitosamente en: $ZIP_FILE"

# Limpieza
rm -rf "$BUILD_DIR"
