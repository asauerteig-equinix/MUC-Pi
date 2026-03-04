#!/usr/bin/env python3
"""
manuell_data_import.py
----------------------
Dieses Skript verbindet sich per FTP mit dem Smartmeter und durchsucht rekursiv den Basisordner "/B:/Log"
nach allen Logdateien (CSV), die dem Muster "Meter_YYYYMMDD.csv" entsprechen.
Jede gefundene Datei wird heruntergeladen, geparst und in die SQLite-Datenbank importiert.
Anschließend wird die lokal zwischengespeicherte Datei gelöscht.
Dadurch entsteht eine einmalige historische Erfassung aller vorhandenen Logdateien in der Datenbank.
"""

import os
import ftplib
import sqlite3
from datetime import datetime
import csv

# === Konfigurationsvariablen ===
FTP_USER      = "ftp"
FTP_PASSWORD  = "ftp"
SMARTMETER_IP = "192.168.100.101"  # IP-Adresse des Smartmeters
FTP_BASE_DIR  = "/B:/Log"          # Basisordner auf dem Smartmeter
# Lokaler Ordner, in den die Dateien heruntergeladen werden
LOCAL_DIR     = os.path.join(os.path.dirname(__file__), "logs")
# SQLite-Datenbank (gleiches File wie im bisherigen Projekt)
DATABASE_FILE = os.path.join(os.path.dirname(__file__), "smartmeter.db")

# Sicherstellen, dass der lokale Ordner existiert
if not os.path.exists(LOCAL_DIR):
    os.makedirs(LOCAL_DIR)

###############################################
# Funktionen für die FTP-Traversierung
###############################################
def list_files(ftp, path):
    """
    Rekursive Funktion, die alle Dateien (vollständige Remote-Pfade) unterhalb von 'path'
    auflistet. Funktioniert folgendermaßen:
      - Es wird versucht, in ein Verzeichnis zu wechseln. Gelingt dies, wird rekursiv gelistet.
      - Ist ein Element kein Verzeichnis, so wird es als Datei behandelt.
    """
    file_list = []
    original_dir = ftp.pwd()
    try:
        ftp.cwd(path)
    except Exception:
        # Kein Verzeichnis, sondern eine Datei
        return [path]
    # Liste alle Elemente im aktuellen Verzeichnis
    try:
        items = ftp.nlst()
    except Exception as e:
        print(f"Fehler beim Auflisten von {path}: {e}")
        return file_list
    for item in items:
        if item in [".", ".."]:
            continue
        full_path = f"{path}/{item}"
        # Versuchen, in den Pfad zu wechseln. Gelingt das, ist es ein Verzeichnis.
        try:
            ftp.cwd(full_path)
            # Es ist ein Verzeichnis – rufe rekursiv die Funktion auf
            file_list.extend(list_files(ftp, full_path))
            ftp.cwd("..")  # Gehe zurück
        except Exception:
            # Exception: Der Wechsel war nicht möglich → es handelt sich um eine Datei
            file_list.append(full_path)
    ftp.cwd(original_dir)
    return file_list

###############################################
# Funktionen für CSV-Parsing und Datenbankimport
###############################################
def process_log_file(local_filepath):
    """
    Parst die CSV-Logdatei, wandelt die benötigten Werte um und gibt eine Liste von Dictionaries zurück.
    Es werden nur folgende Felder verarbeitet:
      - Timestamp (als Integer)
      - DeviceId (als String)
      - Value0 -> Temperatur (als float, geteilt durch 10)
      - Value1 -> Humidity (als float, geteilt durch 10)
    """
    print(f"Verarbeite Datei: {local_filepath}")
    parsed_data = []
    try:
        with open(local_filepath, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile, delimiter=";", quotechar='"')
            for row in reader:
                try:
                    entry = {
                        "timestamp": int(row["Timestamp"]) if row["Timestamp"] else None,
                        "device_id": row["DeviceId"],
                        "temperature": float(row["Value0"]) / 10 if row["Value0"] else None,
                        "humidity": float(row["Value1"]) / 10 if row["Value1"] else None,
                    }
                    parsed_data.append(entry)
                    print(f"Parsed entry: {entry}")
                except Exception as inner_ex:
                    print(f"Fehler beim Verarbeiten einer Zeile: {inner_ex}")
        print(f"Insgesamt wurden {len(parsed_data)} Einträge geparst.")
    except Exception as e:
        print(f"Fehler beim Öffnen/Lesen der Datei {local_filepath}: {e}")
    return parsed_data

def create_database():
    """
    Erstellt die SQLite-Datenbank und die Tabelle 'measurements', falls diese noch nicht existieren.
    Dabei wird ein UNIQUE-Constraint auf (timestamp, device_id) definiert.
    """
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER,
                device_id TEXT,
                temperature REAL,
                humidity REAL,
                CONSTRAINT unique_measurement UNIQUE (timestamp, device_id)
            )
        ''')
        conn.commit()
        conn.close()
        print("Datenbank und Tabelle 'measurements' sind vorhanden.")
    except Exception as e:
        print(f"Fehler beim Erstellen der Datenbank: {e}")

def import_into_db(parsed_data):
    """
    Importiert die geparsten Daten in die SQLite-Datenbank.
    Es wird 'INSERT OR IGNORE' genutzt, um doppelte Einträge zu vermeiden.
    """
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        for entry in parsed_data:
            c.execute('''
                INSERT OR IGNORE INTO measurements (timestamp, device_id, temperature, humidity)
                VALUES (?, ?, ?, ?)
            ''', (entry["timestamp"], entry["device_id"], entry["temperature"], entry["humidity"]))
        conn.commit()
        conn.close()
        print(f"Import abgeschlossen: {len(parsed_data)} Einträge verarbeitet (Duplikate ignoriert).")
    except Exception as e:
        print(f"Fehler beim Import in die Datenbank: {e}")

def cleanup_file(local_filepath):
    """Löscht die lokal gespeicherte Datei, sofern sie existiert."""
    try:
        if os.path.exists(local_filepath):
            os.remove(local_filepath)
            print(f"Lösche lokale Datei: {local_filepath}")
    except Exception as e:
        print(f"Fehler beim Löschen der Datei: {e}")

###############################################
# Hauptprogramm
###############################################
def main():
    # Zunächst sicherstellen, dass die Datenbank und Tabelle existieren.
    create_database()

    try:
        # Verbindung zum FTP-Server herstellen
        print(f"Verbinde zu FTP-Server {SMARTMETER_IP} ...")
        ftp = ftplib.FTP(SMARTMETER_IP)
        ftp.login(FTP_USER, FTP_PASSWORD)
        print("FTP-Login erfolgreich.")

        # Wechsle in den Basisordner
        ftp.cwd(FTP_BASE_DIR)
        print(f"Arbeite im Basisordner: {FTP_BASE_DIR}")

        # Alle Dateien im Verzeichnisbaum unter FTP_BASE_DIR auflisten
        all_files = list_files(ftp, FTP_BASE_DIR)
        ftp.quit()
        print(f"Es wurden insgesamt {len(all_files)} Dateien gefunden.")

        # Filtere nur Logdateien, die mit "Meter_" beginnen und mit ".csv" enden
        log_files = [f for f in all_files if os.path.basename(f).startswith("Meter_") and f.endswith(".csv")]
        print(f"Es wurden {len(log_files)} Logdateien gefunden, die verarbeitet werden.")

        # Für jede Logdatei:
        for remote_file in log_files:
            print(f"\nBearbeite Remote-Datei: {remote_file}")
            # Verbinde erneut zum FTP-Server, um die Datei herunterzuladen
            ftp = ftplib.FTP(SMARTMETER_IP)
            ftp.login(FTP_USER, FTP_PASSWORD)
            try:
                # Extrahiere das Verzeichnis und den Dateinamen
                remote_dir = os.path.dirname(remote_file)
                filename = os.path.basename(remote_file)
                ftp.cwd(remote_dir)
                # Lokaler Speicherpfad: Nutze den Dateinamen und speichere im LOCAL_DIR
                local_filepath = os.path.join(LOCAL_DIR, filename)
                with open(local_filepath, "wb") as local_file:
                    print(f"Lade Datei {filename} herunter ...")
                    ftp.retrbinary(f"RETR {filename}", local_file.write)
                print("Datei heruntergeladen.")
            except Exception as e:
                print(f"Fehler beim Herunterladen von {remote_file}: {e}")
                ftp.quit()
                continue
            ftp.quit()

            # Verarbeite die heruntergeladene Datei
            parsed_data = process_log_file(local_filepath)
            if parsed_data:
                import_into_db(parsed_data)
            # Lösche die lokale Datei nach Verarbeitung
            cleanup_file(local_filepath)
        
        print("\nManueller Datenimport abgeschlossen.")
    except Exception as e:
        print(f"Fehler beim manuellen Datenimport: {e}")

if __name__ == "__main__":
    main()