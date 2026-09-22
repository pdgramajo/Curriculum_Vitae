#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$SCRIPT_DIR/cv" "$@"
EXIT_CODE=$?
if [ "$EXIT_CODE" -ne 0 ]; then
    echo ""
    echo "❌ Ocurrió un error (código $EXIT_CODE). Mirá cvapp.log para más detalle."
    read -p "Presioná Enter para cerrar esta ventana..."
fi
exit "$EXIT_CODE"