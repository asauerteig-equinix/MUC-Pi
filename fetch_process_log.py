#!/usr/bin/env python3
"""
fetch_process_log.py - Dieses Skript verbindet sich per FTP mit dem Smartmeter, 
lädt die täglich generierte Logdatei (CSV) herunter, verarbeitet sie (CSV-Parsen und Import in SQLite) 
und löscht sie im Anschluss lokal.

Konfigurationsvariablen:
- FTP_USER & FTP_PASSWORD: Zugangsdaten zum FTP-Server
- SMARTMETER_IP: IP-Adresse des Smartmeters (im LAN-Netz)
- FTP_BASE_DIR: Basisordner auf dem Smartmeter, in den sich der FTP-User automatisch einloggt.
- LOCAL_DIR: Lokaler Speicherpfad für die heruntergeladenen Dateien.
- Der Remote-Pfad wird dynamisch anhand des aktuellen Datums ermittelt.
"""

import os
import ftplib
from datetime import datetime
import csv

# === Konfigurationsvariablen ===
FTP_USER        = "ftp"
FTP_PASSWORD    = "ftp"
SMARTMETER_IP   = "192.168.100.101"    # IP-Adresse des Smartmeters
FTP_BASE_DIR    = "/B:/Log"            # Ordner, in den der FTP-User automatisch einloggt
LOCAL_DIR       = os.path.join(os.path.dirname(__file__), "logs")  # Lokaler Ordner zum Zwischenspeichern

# Sicherstellen, dass der lokale Ordner existiert
if not os.path.exists(LOCAL_DIR):
    os.makedirs(LOCAL_DIR)

def get_remote_filepath():
    """Berechnet den Remote-Pfad der Logdatei basierend auf dem aktuellen Datum.
    
    Beispiel: Für den 08.04.2025 -> '2025/04/Meter_20250408.csv'
    """
    now = datetime.now()
    year = now.strftime("%Y")          # z. B. "2025"
    month = now.strftime("%m")         # z. B. "04"
    date_str = now.strftime("%Y%m%d")    # z. B. "20250408"
    
    # Der Remote-Pfad relativ zum FTP_BASE_DIR
    remote_dir = f"{year}/{month}"
    remote_file = f"Meter_{date_str}.csv"
    remote_filepath = f"{remote_dir}/{remote_file}"
    return remote_filepath

def get_local_filepath():
    """Bestimmt, unter welchem Namen die Datei lokal gespeichert wird."""
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    local_file = f"Meter_{date_str}.csv"
    return os.path.join(LOCAL_DIR, local_file)

def fetch_log_file():
    """Stellt per FTP eine Verbindung mit dem Smartmeter her, wechselt in den richtigen Unterordner und lädt die aktuelle Logdatei herunter."""
    remote_filepath = get_remote_filepath()  # z. B. "2025/04/Meter_20250408.csv"
    local_filepath = get_local_filepath()
    
    print(f"Aktuelles Datum: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"Berechneter Remote-Pfad: {remote_filepath}")
    print(f"Lokaler Speicherpfad: {local_filepath}")
    
    try:
        print(f"Verbinde zu FTP-Server {SMARTMETER_IP} ...")
        ftp = ftplib.FTP(SMARTMETER_IP)
        ftp.login(FTP_USER, FTP_PASSWORD)
        print("FTP-Login erfolgreich.")
    
        # Wechsel in den entsprechenden Unterordner relativ zum Basisverzeichnis
        remote_dir = os.path.dirname(remote_filepath)
        ftp.cwd(remote_dir)
        print(f"Arbeitsverzeichnis auf FTP-Server gewechselt zu: {remote_dir}")
    
        remote_file = os.path.basename(remote_filepath)
    
        with open(local_filepath, "wb") as local_file:
            print(f"Lade Datei '{remote_file}' herunter ...")
            ftp.retrbinary(f"RETR {remote_file}", local_file.write)
    
        ftp.quit()
        print("Datei erfolgreich heruntergeladen und FTP-Verbindung geschlossen.")
        return local_filepath
    except Exception as e:
        print(f"Fehler beim FTP-Abruf: {e}")
        return None

def process_log_file(local_filepath):
    """
    Parst die CSV-Logdatei und verarbeitet sie.
    Jede Zeile wird als Dictionary eingelesen, einfache Typkonvertierungen werden vorgenommen,
    und als Test werden die geparsten Zeilen ausgegeben.

    Später kann dieser Teil um den Import in die SQLite-Datenbank erweitert werden.
    """
    print(f"Beginne das Parsen der Logdatei: {local_filepath}")
    parsed_data = []
    
    try:
        with open(local_filepath, "r", encoding="utf-8") as csvfile:
            # CSV-Datei wird mit Semikolon (;) als Trenner eingelesen.
            reader = csv.DictReader(csvfile, delimiter=";", quotechar='"')
            for row in reader:
                # Optional: Konvertierung von Werten in den erwarteten Datentypen
                try:
                    row["Timestamp"] = int(row["Timestamp"])
                except Exception:
                    pass
                try:
                    row["Value0"] = float(row["Value0"]) if row["Value0"] else None
                except Exception:
                    pass
                try:
                    row["Timestamp0"] = int(row["Timestamp0"]) if row["Timestamp0"] else None
                except Exception:
                    pass
                try:
                    row["Value1"] = float(row["Value1"]) if row["Value1"] else None
                except Exception:
                    pass
                # Weitere Konvertierungen je nach Bedarf hinzufügen...
                parsed_data.append(row)
                print(row)  # Ausgabe jeder Zeile zum Testen
    
        print(f"Insgesamt wurden {len(parsed_data)} Zeilen aus der Logdatei geparst.")
    except Exception as e:
        print(f"Fehler beim Parsen der Logdatei: {e}")
    
    # Hier kann später der Code zum Import in SQLite ergänzt werden.
    return parsed_data

def cleanup_file(local_filepath):
    """Löscht die lokal gespeicherte Datei, sofern sie existiert."""
    try:
        if os.path.exists(local_filepath):
            os.remove(local_filepath)
            print(f"Lösche lokale Datei: {local_filepath}")
    except Exception as e:
        print(f"Fehler beim Löschen der Datei: {e}")

def main():
    local_filepath = fetch_log_file()
    if local_filepath:
        process_log_file(local_filepath)
        cleanup_file(local_filepath)
    else:
        print("Kein Logfile zum Verarbeiten heruntergeladen.")

if __name__ == "__main__":
    main()