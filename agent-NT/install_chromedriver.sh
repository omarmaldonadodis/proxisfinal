#!/bin/bash

echo "================================================="
echo "  INSTALADOR AUTOMÁTICO DE CHROMEDRIVER"
echo "================================================="

BROWSER_INFO_FILE="$HOME/.config/adspower/browser_info.json"

# -------------------------------------------------
# FUNCIONES
# -------------------------------------------------

get_ads_browser_version() {
    if [[ ! -f "$BROWSER_INFO_FILE" ]]; then
        echo ""
        return 0
    fi

    # Extrae la primera versión que encuentre en el JSON
    version=$(grep -oE '"version":[ ]*"([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)"' "$BROWSER_INFO_FILE" | head -n 1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')

    echo "$version"
}

install_chromedriver() {
    VERSION="$1"

    if [[ -z "$VERSION" ]]; then
        echo "❌ No se puede instalar ChromeDriver: versión vacía."
        exit 1
    fi

    MAJOR=$(echo "$VERSION" | cut -d '.' -f 1)

    echo "▶ Instalando ChromeDriver para versión Chrome $VERSION (major $MAJOR)"

    # URL oficial
    JSON_URL="https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"

    echo "→ Buscando ChromeDriver compatible..."

    # Descargar JSON temporalmente
    TMP_FILE="/tmp/chrome_versions.json"
    curl -s "$JSON_URL" -o "$TMP_FILE"

    DRIVER_URL=$(cat "$TMP_FILE" | grep -A10 "\"version\": \"$VERSION\"" | grep "mac-x64" | grep "chromedriver" | head -n1 | sed -E 's/.*"url": "(.*)".*/\1/')

    # Si no encuentra coincidencia exacta, busca por major version
    if [[ -z "$DRIVER_URL" ]]; then
        DRIVER_URL=$(grep -A10 "\"version\": \""$MAJOR"." "$TMP_FILE" |
                     grep "mac-x64" |
                     grep "chromedriver" |
                     head -n1 |
                     sed -E 's/.*"url": "(.*)".*/\1/')
    fi

    if [[ -z "$DRIVER_URL" ]]; then
        echo "❌ No se encontró ChromeDriver compatible."
        exit 1
    fi

    echo "→ Descargando desde:"
    echo "$DRIVER_URL"

    ZIP_FILE="/tmp/chromedriver.zip"
    curl -L "$DRIVER_URL" -o "$ZIP_FILE"

    echo "→ Extrayendo..."
    unzip -o "$ZIP_FILE" -d /tmp/chromedriver_dir

    echo "→ Moviendo a /usr/local/bin"
    sudo mv /tmp/chromedriver_dir/chromedriver /usr/local/bin/chromedriver
    sudo chmod +x /usr/local/bin/chromedriver

    echo "✅ ChromeDriver instalado correctamente."
}

# -------------------------------------------------
# MENÚ
# -------------------------------------------------

echo ""
echo "Seleccione el modo:"
echo "1) Detectar versión del navegador de AdsPower"
echo "2) Instalar ChromeDriver manualmente (120–143)"
echo ""
read -p "Opción: " OPTION

case "$OPTION" in
    1)
        VERSION=$(get_ads_browser_version)

        if [[ -z "$VERSION" ]]; then
            echo "❌ No se pudo obtener la versión del navegador automáticamente."
            echo "   → Usa la opción 2 para instalar manualmente."
            exit 1
        fi

        echo "✔ Versión detectada: $VERSION"
        install_chromedriver "$VERSION"
        ;;
    2)
        read -p "Ingrese la versión mayor de Chrome (ej: 120, 121, 122...): " MANUAL_VERSION
        if ! [[ "$MANUAL_VERSION" =~ ^[0-9]+$ ]]; then
            echo "❌ Versión inválida."
            exit 1
        fi

        # Simular versión completa (Google usa 120.0.0.0 para descargar)
        FULL="${MANUAL_VERSION}.0.0.0"
        install_chromedriver "$FULL"
        ;;
    *)
        echo "❌ Opción no válida."
        exit 1
        ;;
esac
