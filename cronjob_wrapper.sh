#!/bin/bash
# Cronjob-Wrapper für den regelmäßigen FTP-Abruf
# Wird von cron aufgerufen und führt das Python-Skript aus

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Virtuelle Umgebung aktivieren (falls vorhanden)
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Python-Skript ausführen
/usr/bin/python3 "$PROJECT_DIR/cronjob_fetch.py"
