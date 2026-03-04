#!/bin/bash
# Manual Data Import - Lädt alle historischen Logdateien
# Wird einmalig zur Initialisierung ausgeführt

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Virtuelle Umgebung aktivieren (falls vorhanden)
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

/usr/bin/python3 << 'EOF'
import sys
sys.path.insert(0, '/home/pi/smartmeter_project')
from ftp_handler import manual_import_all_logfiles

print("Starte manuellen Import aller Logdateien...")
success = manual_import_all_logfiles()
if success:
    print("Import erfolgreich abgeschlossen!")
else:
    print("Import fehlgeschlagen!")
    sys.exit(1)
EOF
