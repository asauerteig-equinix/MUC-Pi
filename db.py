#!/usr/bin/env python3
"""
db.py - Datenbank-Verwaltung mit Fehlerbehandlung
"""

import sqlite3
import os
import logging
from config import DATABASE_FILE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """
    Stellt eine Datenbankverbindung her.
    Falls die Datenbank beschädigt ist, gibt es einen Fehler zurück.
    """
    try:
        if not os.path.exists(DATABASE_FILE):
            logger.info(f"Datenbank existiert nicht, erstelle sie: {DATABASE_FILE}")
            _create_database()
        
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        # Test: Können wir auf die Tabelle zugreifen?
        conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return conn
    except sqlite3.DatabaseError as e:
        logger.error(f"Datenbankfehler: {e}")
        raise Exception(f"Datenbank beschädigt oder nicht verfügbar: {e}")
    except Exception as e:
        logger.error(f"Fehler beim Datenbankzugriff: {e}")
        raise

def _create_database():
    """
    Erstellt die Datenbank mit allen notwendigen Tabellen.
    """
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        
        # Tabelle für Sensoren
        c.execute('''
            CREATE TABLE IF NOT EXISTS sensors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT UNIQUE NOT NULL,
                sensor_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabelle für Messungen
        c.execute('''
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                temperature REAL,
                humidity REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(device_id) REFERENCES sensors(device_id)
            )
        ''')
        
        # Index für schnellere Abfragen
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_measurements_device_timestamp 
            ON measurements(device_id, timestamp DESC)
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Datenbank erfolgreich erstellt.")
    except Exception as e:
        logger.error(f"Fehler beim Erstellen der Datenbank: {e}")
        raise

def get_sensors():
    """Holt alle konfigurierten Sensoren."""
    try:
        conn = get_db_connection()
        sensors = conn.execute("SELECT * FROM sensors ORDER BY sensor_name").fetchall()
        conn.close()
        return sensors
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Sensoren: {e}")
        return []

def add_sensor(device_id, sensor_name):
    """Fügt einen neuen Sensor hinzu."""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO sensors (device_id, sensor_name) VALUES (?, ?)", 
                  (device_id, sensor_name))
        conn.commit()
        conn.close()
        logger.info(f"Sensor hinzugefügt: {sensor_name} ({device_id})")
        return True
    except sqlite3.IntegrityError:
        logger.error(f"Sensor mit dieser Device-ID existiert bereits: {device_id}")
        return False
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen des Sensors: {e}")
        return False

def update_sensor(device_id, sensor_name):
    """Aktualisiert die Namen eines Sensors."""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE sensors SET sensor_name = ? WHERE device_id = ?",
                  (sensor_name, device_id))
        conn.commit()
        rows_changed = c.rowcount
        conn.close()
        if rows_changed > 0:
            logger.info(f"Sensor aktualisiert: {device_id} -> {sensor_name}")
            return True
        return False
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Sensors: {e}")
        return False

def delete_sensor(device_id):
    """Löscht einen Sensor und seine Messungen."""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("DELETE FROM measurements WHERE device_id = ?", (device_id,))
        c.execute("DELETE FROM sensors WHERE device_id = ?", (device_id,))
        conn.commit()
        conn.close()
        logger.info(f"Sensor gelöscht: {device_id}")
        return True
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Sensors: {e}")
        return False

def get_latest_measurement(device_id):
    """Holt die neueste Messung für einen Sensor."""
    try:
        conn = get_db_connection()
        measurement = conn.execute(
            "SELECT * FROM measurements WHERE device_id = ? ORDER BY timestamp DESC LIMIT 1",
            (device_id,)
        ).fetchone()
        conn.close()
        return measurement
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der neuesten Messung: {e}")
        return None

def get_measurements(device_id, time_range_seconds):
    """Holt Messungen innerhalb eines Zeitraums."""
    try:
        import time
        current_time = int(time.time())
        lower_bound = current_time - time_range_seconds
        
        conn = get_db_connection()
        measurements = conn.execute(
            "SELECT * FROM measurements WHERE device_id = ? AND timestamp >= ? ORDER BY timestamp ASC",
            (device_id, lower_bound)
        ).fetchall()
        conn.close()
        return measurements
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Messungen: {e}")
        return []

def get_all_measurements(limit=1000, offset=0):
    """Holt alle Messungen mit Pagination."""
    try:
        conn = get_db_connection()
        measurements = conn.execute(
            "SELECT m.*, s.sensor_name FROM measurements m LEFT JOIN sensors s ON m.device_id = s.device_id ORDER BY m.timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
        conn.close()
        return measurements
    except Exception as e:
        logger.error(f"Fehler beim Abrufen aller Messungen: {e}")
        return []

def get_measurements_count():
    """Holt die Gesamtanzahl der Messungen."""
    try:
        conn = get_db_connection()
        count = conn.execute("SELECT COUNT(*) as total FROM measurements").fetchone()
        conn.close()
        return count['total'] if count else 0
    except Exception as e:
        logger.error(f"Fehler beim Zählen der Messungen: {e}")
        return 0

def update_measurement(measurement_id, temperature, humidity):
    """Aktualisiert Temperatur und Luftfeuchtigkeit einer Messung."""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            "UPDATE measurements SET temperature = ?, humidity = ? WHERE id = ?",
            (temperature, humidity, measurement_id)
        )
        conn.commit()
        rows_changed = c.rowcount
        conn.close()
        if rows_changed > 0:
            logger.info(f"Messung {measurement_id} aktualisiert")
            return True
        return False
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren der Messung: {e}")
        return False

def delete_measurement(measurement_id):
    """Löscht eine einzelne Messung."""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("DELETE FROM measurements WHERE id = ?", (measurement_id,))
        conn.commit()
        rows_changed = c.rowcount
        conn.close()
        if rows_changed > 0:
            logger.info(f"Messung {measurement_id} gelöscht")
            return True
        return False
    except Exception as e:
        logger.error(f"Fehler beim Löschen der Messung: {e}")
        return False

def insert_measurement(device_id, timestamp, temperature, humidity):
    """Fügt eine neue Messung in die Datenbank ein."""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO measurements (device_id, timestamp, temperature, humidity) VALUES (?, ?, ?, ?)",
            (device_id, timestamp, temperature, humidity)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Einfügen der Messung: {e}")
        return False

def db_health_check():
    """Überprüft den Status der Datenbank."""
    try:
        conn = get_db_connection()
        conn.execute("SELECT COUNT(*) FROM sensors")
        conn.close()
        return True, "Datenbank OK"
    except Exception as e:
        return False, str(e)
