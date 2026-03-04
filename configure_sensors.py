#!/usr/bin/env python3
"""
configure_sensors.py
--------------------
Dieses Skript erstellt (nach Rückfrage) die Tabelle 'sensors' in der SQLite-Datenbank neu. 
Die Tabelle enthält die Zuordnung von DeviceID zu einem lesbaren Namen.
Bei jedem Durchlauf, wenn bestätigt wird, wird die bestehende Tabelle gelöscht und neu angelegt.
Beim Hinzufügen eines Sensors musst du nur den nummerischen Teil der DeviceID angeben, 
das Script ergänzt automatisch "WEP-" davor und "-02-27" danach.
"""

import sqlite3
import os

# Konfigurationsvariable: Pfad zur Datenbank
DATABASE_FILE = os.path.join(os.path.dirname(__file__), "smartmeter.db")

def confirm_configuration():
    """
    Fragt ab, ob die Sensor-Konfiguration neu durchgeführt werden soll.
    Nur bei Bestätigung wird die bestehende Tabelle gelöscht.
    """
    confirmation = input("Soll die Sensor-Konfiguration neu durchgeführt werden? Dabei wird die bestehende Tabelle 'sensors' gelöscht. (ja/nein): ").strip().lower()
    return confirmation == "ja"

def create_sensor_table():
    """Löscht die Tabelle 'sensors', falls vorhanden, und legt sie neu an."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        # Tabelle löschen, falls vorhanden
        c.execute("DROP TABLE IF EXISTS sensors")
        # Neue Tabelle erstellen mit UNIQUE auf device_id
        c.execute('''
            CREATE TABLE sensors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT UNIQUE,
                sensor_name TEXT
            )
        ''')
        conn.commit()
        conn.close()
        print("Tabelle 'sensors' wurde neu angelegt.")
    except Exception as e:
        print(f"Fehler beim Erstellen der Tabelle: {e}")

def insert_sensor(device_id_number, sensor_name):
    """
    Ergänzt die DeviceID automatisch.
    Aus dem eingegebenen nummerischen Teil (z. B. '00001234')
    wird die vollständige DeviceID 'WEP-00001234-02-27'
    """
    full_device_id = f"WEP-{device_id_number}-02-27"
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO sensors (device_id, sensor_name) VALUES (?, ?)", 
                  (full_device_id, sensor_name))
        conn.commit()
        conn.close()
        print(f"Sensor hinzugefügt: {full_device_id} -> {sensor_name}")
    except Exception as e:
        print(f"Fehler beim Einfügen von {full_device_id}: {e}")

def input_sensors():
    """
    Fordert den Benutzer in einer Schleife zur Eingabe von Sensoren auf.
    Zum Beenden des Eingabeprozesses wird 'exit' als DeviceID eingegeben.
    """
    print("\nGeben Sie Sensoren ein. Um den Eingabeprozess zu beenden, geben Sie 'exit' als DeviceID ein.")
    while True:
        device_id_number = input("Geben Sie den nummerischen Teil der DeviceID ein (z. B. 00001234): ").strip()
        if device_id_number.lower() == 'exit':
            break
        sensor_name = input("Lesbarer Name des Sensors: ").strip()
        if device_id_number and sensor_name:
            insert_sensor(device_id_number, sensor_name)
        else:
            print("Leere Eingabe – bitte beide Werte angeben.")

def main():
    if confirm_configuration():
        create_sensor_table()
        input_sensors()
        print("Sensor-Konfiguration abgeschlossen.")
    else:
        print("Sensor-Konfiguration wurde abgebrochen. Keine Änderungen vorgenommen.")

if __name__ == "__main__":
    main()