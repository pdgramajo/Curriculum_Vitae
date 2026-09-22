#!/bin/bash

# Buscar el directorio del proyecto buscando el .venv
find_project_dir() {
    local start="$1"
    while [ "$start" != "/" ]; do
        if [ -d "$start/.venv" ]; then
            echo "$start"
            return
        fi
        start="$(dirname "$start")"
    done
}

# Obtener directorio base
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(find_project_dir "$SCRIPT_DIR")"

if [ -z "$PROJECT_DIR" ]; then
    echo "❌ Error: No se encontró la carpeta del proyecto"
    read -p "Presiona Enter para salir..."
    exit 1
fi

cd "$PROJECT_DIR"
source .venv/bin/activate
python3 cv_tui.py
EXIT_CODE=$?
deactivate
exit $EXIT_CODE