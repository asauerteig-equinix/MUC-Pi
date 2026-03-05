#!/bin/bash
# Manual Data Import - Interaktiver Import mit Zeitraum-Optionen
# Laden Sie alle oder ausgewählte historische Logdateien herunter

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "========================================"
echo "SMARTMETER - Manueller Datenimport"
echo "========================================"
echo ""

# Prüfe ob venv existiert
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "⚠️  Warnung: Virtuelle Umgebung nicht gefunden"
fi

# Führe das interaktive Importskript aus
python3 interactive_import.py

exit $?
