#!/usr/bin/env python3
"""
ftp_handler.py - FTP-Verbindung und CSV-Import
"""

import os
import ftplib
import csv
import logging
from datetime import datetime
from config import FTP_USER, FTP_PASSWORD, SMARTMETER_IP, FTP_BASE_DIR, LOGS_DIR
from db import insert_measurement, get_sensors

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_remote_filepath():
    """Bestimmt den Remote-Pfad der heutigen Logdatei."""
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    date_str = now.strftime("%Y%m%d")
    remote_dir = f"{year}/{month}"
    remote_file = f"Meter_{date_str}.csv"
    return f"{remote_dir}/{remote_file}"

def get_local_filepath():
    """Bestimmt den lokalen Speicherpfad."""
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    return os.path.join(LOGS_DIR, f"Meter_{date_str}.csv")

def connect_ftp():
    """Verbindet sich mit dem FTP-Server."""
    try:
        ftp = ftplib.FTP(SMARTMETER_IP)
        ftp.login(FTP_USER, FTP_PASSWORD)
        ftp.cwd(FTP_BASE_DIR)
        logger.info(f"FTP-Verbindung zu {SMARTMETER_IP} erfolgreich")
        return ftp
    except Exception as e:
        logger.error(f"FTP-Verbindungsfehler: {e}")
        raise

def download_logfile():
    """Lädt die heutige Logdatei herunter."""
    try:
        ftp = connect_ftp()
        remote_file = get_remote_filepath()
        local_file = get_local_filepath()
        
        with open(local_file, 'wb') as f:
            ftp.retrbinary(f'RETR {remote_file}', f.write)
        
        ftp.quit()
        logger.info(f"Datei heruntergeladen: {remote_file} -> {local_file}")
        return local_file
    except Exception as e:
        logger.error(f"Fehler beim Herunterladen der Logdatei: {e}")
        return None

def parse_csv_file(filepath):
    """
    Parst die CSV-Datei und extrahiert Temperatur und Luftfeuchtigkeit.
    
    Format der CSV:
    Timestamp;DeviceId;Value0;Scale0;Unit0;...;Value1;Scale1;Unit1;...
    """
    measurements = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                try:
                    device_id = row.get('DeviceId', '').strip()
                    timestamp = int(row.get('Timestamp', 0))
                    
                    # Value0 = Temperatur, Value1 = Luftfeuchtigkeit
                    value0 = row.get('Value0', '').strip()
                    value1 = row.get('Value1', '').strip()
                    
                    # Scale-Werte anwenden
                    scale0_str = row.get('Scale0', '').strip()
                    scale1_str = row.get('Scale1', '').strip()
                    
                    temperature = None
                    humidity = None
                    
                    if value0:
                        try:
                            temp_val = float(value0)
                            scale0 = float(scale0_str) if scale0_str else 1.0
                            temperature = temp_val * scale0
                        except:
                            pass
                    
                    if value1:
                        try:
                            hum_val = float(value1)
                            scale1 = float(scale1_str) if scale1_str else 1.0
                            humidity = hum_val * scale1
                        except:
                            pass
                    
                    if device_id and timestamp:
                        measurements.append({
                            'device_id': device_id,
                            'timestamp': timestamp,
                            'temperature': temperature,
                            'humidity': humidity
                        })
                except Exception as row_error:
                    logger.warning(f"Fehler beim Parsen einer Zeile: {row_error}")
                    continue
        
        logger.info(f"{len(measurements)} Messungen aus CSV geparst")
        return measurements
    except Exception as e:
        logger.error(f"Fehler beim Parsen der CSV-Datei: {e}")
        return []

def import_measurements(measurements):
    """Importiert Messungen in die Datenbank."""
    imported_count = 0
    for m in measurements:
        if insert_measurement(m['device_id'], m['timestamp'], m['temperature'], m['humidity']):
            imported_count += 1
    
    logger.info(f"{imported_count}/{len(measurements)} Messungen importiert")
    return imported_count

def fetch_and_process_logfile():
    """Hauptfunktion: Lädt die Logdatei herunter, parst sie und importiert die Daten."""
    try:
        logger.info("Starte FTP-Abruf...")
        
        # Datei herunterladen
        local_file = download_logfile()
        if not local_file:
            return False
        
        # CSV parsen
        measurements = parse_csv_file(local_file)
        if not measurements:
            logger.warning("Keine Messungen in der Datei gefunden")
            return False
        
        # In Datenbank importieren
        imported = import_measurements(measurements)
        
        # Lokale Datei löschen
        try:
            os.remove(local_file)
            logger.info(f"Lokale Datei gelöscht: {local_file}")
        except:
            pass
        
        return imported > 0
    except Exception as e:
        logger.error(f"Fehler beim Abruf und Verarbeitung: {e}")
        return False

def list_remote_files_recursive(ftp, path="/"):
    """
    Rekursiv alle CSV-Dateien im Remote-Verzeichnis auflisten.
    Wird für den manuellen Import verwendet.
    """
    file_list = []
    original_dir = ftp.pwd()
    try:
        ftp.cwd(path)
    except:
        return file_list
    
    try:
        items = ftp.nlst()
    except:
        return file_list
    
    for item in items:
        try:
            item_path = f"{path}/{item}".replace("//", "/")
            try:
                ftp.cwd(item_path)
                ftp.cwd(path)
                # Es ist ein Verzeichnis
                file_list.extend(list_remote_files_recursive(ftp, item_path))
            except:
                # Es ist eine Datei
                if item.startswith("Meter_") and item.endswith(".csv"):
                    file_list.append(item_path)
        except:
            pass
    
    ftp.cwd(original_dir)
    return file_list

def manual_import_all_logfiles():
    """
    Lädt alle historischen Logdateien herunter und importiert sie.
    Wird einmalig zur Initialisierung verwendet.
    """
    try:
        logger.info("Starte manuellen Import aller Logdateien...")
        ftp = connect_ftp()
        
        # Alle CSV-Dateien
        files = list_remote_files_recursive(ftp, FTP_BASE_DIR)
        logger.info(f"Gefundene Dateien: {len(files)}")
        
        total_imported = 0
        for remote_file in sorted(files):
            try:
                local_file = get_local_filepath()
                with open(local_file, 'wb') as f:
                    ftp.retrbinary(f'RETR {remote_file}', f.write)
                
                measurements = parse_csv_file(local_file)
                imported = import_measurements(measurements)
                total_imported += imported
                
                os.remove(local_file)
                logger.info(f"Import von {remote_file}: {imported} Messungen")
            except Exception as e:
                logger.error(f"Fehler beim Import von {remote_file}: {e}")
                continue
        
        ftp.quit()
        logger.info(f"Manueller Import abgeschlossen. Insgesamt {total_imported} Messungen importiert.")
        return True
    except Exception as e:
        logger.error(f"Fehler beim manuellen Import: {e}")
        return False

if __name__ == "__main__":
    # Test
    fetch_and_process_logfile()
