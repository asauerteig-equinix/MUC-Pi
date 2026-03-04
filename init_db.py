#!/usr/bin/env python3
"""
init_db.py - Datenbank-Initialisierung
Dieses Skript erstellt die Datenbank neu und richtet das System ein.
"""

import sys
import os

# Stelle sicher, dass wir das aktuelle Verzeichnis verwenden
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import _create_database, add_sensor
from config import DATABASE_FILE
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Initialisiert die Datenbank und fügt Test-Sensoren hinzu."""
    
    print("=" * 60)
    print("Smartmeter Datenbank Initialisierung")
    print("=" * 60)
    print()
    
    # Datenbank erstellen
    logger.info("Erstelle Datenbank...")
    try:
        _create_database()
        logger.info("✓ Datenbank erfolgreich erstellt")
        print(f"  Speicherort: {DATABASE_FILE}")
    except Exception as e:
        logger.error(f"✗ Fehler: {e}")
        sys.exit(1)
    
    print()
    print("Datenbank ist bereit für Sensoren")
    print()
    print("Nächste Schritte:")
    print("  1. Starten Sie die Webanwendung:")
    print("     python3 app.py")
    print()
    print("  2. Öffnen Sie http://localhost:5000")
    print()
    print("  3. Gehen Sie zu '/sensors' um Sensoren hinzuzufügen")
    print()
    print("  4. (Optional) Für historische Daten:")
    print("     bash manual_import.sh")
    print()

if __name__ == "__main__":
    init_database()
