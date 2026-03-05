#!/usr/bin/env python3
"""
interactive_import.py - Interaktiver manueller Import mit Zeitraum-Optionen
Bietet Menü für: Alle Daten, dieses Jahr, dieser Monat
"""

import sys
import os
from datetime import datetime
import time

# Stelle sicher dass wir im richtigen Verzeichnis sind
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

from ftp_handler import connect_ftp, list_remote_files_recursive, parse_csv_file, import_measurements
from config import FTP_BASE_DIR
from db import get_measurements_count

# Farben für Output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_header():
    """Zeige Kopfzeile."""
    print(f"\n{BOLD}{BLUE}{'='*60}")
    print("      SMARTMETER - INTERAKTIVER DATENIMPORT")
    print(f"{'='*60}{RESET}\n")

def print_menu():
    """Zeige Importmenü."""
    now = datetime.now()
    current_year = now.year
    current_month = now.strftime("%B %Y")
    
    print(f"{YELLOW}Wähle den gewünschten Importbereich:{RESET}\n")
    print(f"  {BOLD}1){RESET} Alle Daten (komplett)")
    print(f"  {BOLD}2){RESET} Dieses Jahr ({current_year})")
    print(f"  {BOLD}3){RESET} Dieser Monat ({current_month})")
    print(f"  {BOLD}0){RESET} Abbrechen")
    print()

def get_choice():
    """Frage nach Menüauswahl."""
    while True:
        try:
            choice = input(f"{BLUE}Deine Auswahl (0-3): {RESET}").strip()
            if choice in ['0', '1', '2', '3']:
                return choice
            print(f"{RED}Ungültige Eingabe! Bitte 0-3 eingeben.{RESET}")
        except KeyboardInterrupt:
            print(f"\n{YELLOW}Import abgebrochen.{RESET}")
            sys.exit(0)

def filter_files_by_range(files, import_type):
    """Filtert Dateien nach Importtyp."""
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    filtered = []
    
    for filepath in files:
        # Extrahiere Datum aus Dateinamen: "Meter_YYYYMMDD.csv"
        try:
            # filepath könnte so aussehen: "/2024/12/Meter_20241215.csv"
            filename = os.path.basename(filepath)  # "Meter_20241215.csv"
            if not filename.startswith("Meter_") or not filename.endswith(".csv"):
                continue
            
            date_str = filename.split("_")[1].split(".")[0]  # "20241215"
            year = int(date_str[:4])
            month = int(date_str[4:6])
            
            if import_type == "1":  # Alle
                filtered.append(filepath)
            elif import_type == "2":  # Dieses Jahr
                if year == current_year:
                    filtered.append(filepath)
            elif import_type == "3":  # Dieser Monat
                if year == current_year and month == current_month:
                    filtered.append(filepath)
        except:
            continue
    
    return sorted(filtered)

def format_filesize(bytes):
    """Konvertiere Bytes zu lesbarem Format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024
    return f"{bytes:.1f} TB"

def format_duration(seconds):
    """Konvertiere Sekunden zu lesbarem Format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}min"
    else:
        return f"{seconds/3600:.1f}h"

def confirm_import(import_type, file_count, estimated_time):
    """Bestätigung vor dem Import."""
    type_labels = {
        "1": "ALLE DATEN",
        "2": f"DIESES JAHR ({datetime.now().year})",
        "3": f"DIESER MONAT ({datetime.now().strftime('%B %Y')})"
    }
    
    print(f"\n{BOLD}{YELLOW}{'='*60}")
    print("IMPORTBESTÄTIGUNG")
    print(f"{'='*60}{RESET}")
    print(f"  Bereich:     {BOLD}{type_labels.get(import_type, 'Unbekannt')}{RESET}")
    print(f"  Dateien:     {BOLD}{GREEN}{file_count}{RESET} Logdateien")
    print(f"  Geschätzte Dauer: {BOLD}{file_count * 7}s - {file_count * 10}s{RESET} (~{format_duration(file_count * 7)} bis {format_duration(file_count * 10)})")
    print(f"\n{RED}⚠️  WARNUNG: Dies kann mehrere Stunden dauern!{RESET}")
    print(f"{YELLOW}Die vorhandenen Daten werden nicht gelöscht.{RESET}\n")
    
    while True:
        response = input(f"{BLUE}Wirklich fortfahren? (ja/nein): {RESET}").strip().lower()
        if response in ['ja', 'j', 'yes', 'y']:
            return True
        elif response in ['nein', 'n', 'no']:
            print(f"{YELLOW}Import abgebrochen.{RESET}")
            return False
        else:
            print(f"{RED}Bitte 'ja' oder 'nein' eingeben.{RESET}")

def run_import(import_type, filtered_files):
    """Führe den Import aus."""
    print(f"\n{BOLD}{GREEN}Starte Import...{RESET}\n")
    
    try:
        ftp = connect_ftp()
        
        total_imported = 0
        failed_files = 0
        start_time = time.time()
        
        for idx, remote_file in enumerate(filtered_files, 1):
            try:
                file_num = idx
                total_files = len(filtered_files)
                progress = (idx / total_files) * 100
                
                # Fortschritt anzeigen
                print(f"[{file_num:3d}/{total_files}] ({progress:5.1f}%) {remote_file:<50}", end="", flush=True)
                
                # Download
                file_start = time.time()
                local_file = os.path.join(PROJECT_DIR, "logs", os.path.basename(remote_file))
                os.makedirs(os.path.dirname(local_file), exist_ok=True)
                
                with open(local_file, 'wb') as f:
                    ftp.retrbinary(f'RETR {remote_file}', f.write)
                
                # Parse and Import
                measurements = parse_csv_file(local_file)
                imported = import_measurements(measurements)
                total_imported += imported
                
                # Cleanup
                os.remove(local_file)
                
                elapsed = time.time() - file_start
                print(f" {GREEN}✓{RESET} {imported} Messungen ({elapsed:.1f}s)")
                
            except Exception as e:
                failed_files += 1
                print(f" {RED}✗ FEHLER: {str(e)[:30]}{RESET}")
                continue
        
        ftp.quit()
        
        total_time = time.time() - start_time
        
        # Zusammenfassung
        print(f"\n{BOLD}{GREEN}{'='*60}")
        print("IMPORT ABGESCHLOSSEN")
        print(f"{'='*60}{RESET}")
        print(f"  {GREEN}✓ Messungen importiert: {total_imported}{RESET}")
        print(f"  {RED}✗ Fehler: {failed_files}{RESET}")
        print(f"  ⏱️  Gesamtdauer: {format_duration(total_time)}")
        print(f"  ⚡ Durchschnitt: {format_duration(total_time / len(filtered_files))} pro Datei")
        
        db_count = get_measurements_count()
        print(f"  📊 Gesamte Messungen in DB: {db_count}")
        print(f"{GREEN}{'='*60}{RESET}\n")
        
        return True
        
    except Exception as e:
        print(f"\n{RED}Fehler beim Import: {e}{RESET}")
        return False

def main():
    """Hauptprogramm."""
    print_header()
    
    try:
        # Verbindung testen
        print(f"{YELLOW}Verbinde zu FTP-Server...{RESET}")
        ftp = connect_ftp()
        
        # Dateien auflisten
        print(f"{YELLOW}Suche Logdateien...{RESET}")
        all_files = list_remote_files_recursive(ftp, FTP_BASE_DIR)
        ftp.quit()
        
        print(f"{GREEN}✓ {len(all_files)} Logdateien gefunden{RESET}\n")
        
        # Menü
        print_menu()
        choice = get_choice()
        
        if choice == "0":
            print(f"{YELLOW}Import abgebrochen.{RESET}\n")
            return
        
        # Dateien filtern
        filtered_files = filter_files_by_range(all_files, choice)
        
        if not filtered_files:
            print(f"{RED}Keine Dateien für diesen Zeitraum gefunden!{RESET}\n")
            return
        
        # Bestätigung
        if not confirm_import(choice, len(filtered_files), len(filtered_files) * 7):
            return
        
        # Import durchführen
        run_import(choice, filtered_files)
        
    except Exception as e:
        print(f"{RED}Fehler: {e}{RESET}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
