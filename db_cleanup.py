#!/usr/bin/env python3
"""
db_cleanup.py - Datenbank-Archivierung und Bereinigung

Archiviert Messdaten älter als ARCHIVE_DAYS_THRESHOLD in eine separate
SQLite-Archiv-Datenbank und hält die Hauptdatenbank schlank.

Die Archiv-Datenbank wird nach Jahr benannt (z.B. archiv_2025.db)
damit historische Daten nicht verloren gehen.

Empfohlen: Einmal täglich per Cronjob ausführen.
"""

import sqlite3
import os
import time
import logging
from datetime import datetime
from config import DATABASE_FILE, LOG_FILE

# Konfiguration
ARCHIVE_DAYS_THRESHOLD = 35  # Daten älter als 35 Tage archivieren (5 Tage Puffer über 30-Tage-Anzeige)
ARCHIVE_DIR = os.path.join(os.path.dirname(__file__), "archiv")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_archive_db_path():
    """Gibt den Pfad zur Archiv-Datenbank für das aktuelle Archivjahr zurück."""
    if not os.path.exists(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR)
    
    # Archiv nach Jahr der ältesten Daten benennen
    year = datetime.now().year
    return os.path.join(ARCHIVE_DIR, f"archiv_{year}.db")


def init_archive_db(archive_path):
    """Erstellt die Archiv-Datenbank mit dem gleichen Schema wie die Hauptdatenbank."""
    conn = sqlite3.connect(archive_path)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            temperature REAL,
            humidity REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_archive_device_timestamp 
        ON measurements(device_id, timestamp DESC)
    ''')
    
    conn.commit()
    return conn


def run_cleanup():
    """
    Hauptfunktion: Archiviert alte Daten und bereinigt die Hauptdatenbank.
    
    Ablauf:
    1. Berechne Schwellenwert-Timestamp
    2. Kopiere alte Messungen in Archiv-DB
    3. Lösche archivierte Messungen aus Haupt-DB
    4. VACUUM um Speicherplatz freizugeben
    """
    cutoff_timestamp = int(time.time()) - (ARCHIVE_DAYS_THRESHOLD * 86400)
    cutoff_date = datetime.fromtimestamp(cutoff_timestamp).strftime('%d.%m.%Y %H:%M')
    
    logger.info(f"Starte DB-Bereinigung. Archiviere Daten älter als {cutoff_date}")
    
    # Hauptdatenbank öffnen
    if not os.path.exists(DATABASE_FILE):
        logger.info("Keine Datenbank vorhanden, nichts zu tun.")
        return
    
    main_conn = sqlite3.connect(DATABASE_FILE)
    main_conn.row_factory = sqlite3.Row
    
    # Zähle zu archivierende Einträge
    count = main_conn.execute(
        "SELECT COUNT(*) as cnt FROM measurements WHERE timestamp < ?",
        (cutoff_timestamp,)
    ).fetchone()["cnt"]
    
    if count == 0:
        logger.info("Keine alten Daten zum Archivieren vorhanden.")
        main_conn.close()
        return
    
    logger.info(f"{count} Messungen werden archiviert...")
    
    # Archiv-DB vorbereiten
    archive_path = get_archive_db_path()
    archive_conn = init_archive_db(archive_path)
    
    # Daten in Batches archivieren (um RAM-Nutzung gering zu halten)
    batch_size = 5000
    total_archived = 0
    
    while True:
        rows = main_conn.execute(
            "SELECT device_id, timestamp, temperature, humidity, created_at "
            "FROM measurements WHERE timestamp < ? LIMIT ?",
            (cutoff_timestamp, batch_size)
        ).fetchall()
        
        if not rows:
            break
        
        # In Archiv einfügen
        archive_conn.executemany(
            "INSERT INTO measurements (device_id, timestamp, temperature, humidity, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            [(r["device_id"], r["timestamp"], r["temperature"], r["humidity"], r["created_at"]) for r in rows]
        )
        archive_conn.commit()
        
        # Aus Hauptdatenbank löschen (die gleichen IDs)
        ids = [r["device_id"] for r in rows]
        timestamps = [r["timestamp"] for r in rows]
        
        # Batch-Delete über Timestamp-Range dieses Batches
        min_ts = min(timestamps)
        max_ts = max(timestamps)
        main_conn.execute(
            "DELETE FROM measurements WHERE timestamp >= ? AND timestamp <= ? AND timestamp < ?",
            (min_ts, max_ts, cutoff_timestamp)
        )
        main_conn.commit()
        
        total_archived += len(rows)
        logger.info(f"  Fortschritt: {total_archived}/{count} archiviert...")
    
    archive_conn.close()
    
    # VACUUM um Speicherplatz freizugeben
    logger.info("Führe VACUUM aus (Speicherplatz freigeben)...")
    main_conn.execute("VACUUM")
    main_conn.close()
    
    # Dateigrößen loggen
    main_size = os.path.getsize(DATABASE_FILE) / (1024 * 1024)
    archive_size = os.path.getsize(archive_path) / (1024 * 1024)
    
    logger.info(f"Bereinigung abgeschlossen!")
    logger.info(f"  Archiviert: {total_archived} Messungen → {archive_path}")
    logger.info(f"  Hauptdatenbank: {main_size:.1f} MB")
    logger.info(f"  Archiv: {archive_size:.1f} MB")


if __name__ == "__main__":
    run_cleanup()
