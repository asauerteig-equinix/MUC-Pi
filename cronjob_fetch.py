#!/usr/bin/env python3
"""
cronjob_fetch.py - Intelligenter Abruf mit Zeitsteuerung
- 06:00 - 01:00 Uhr: Abruf alle 15 Minuten
- 01:00 - 06:00 Uhr: Abruf alle 30 Minuten
"""

import time
from datetime import datetime
import logging
from ftp_handler import fetch_and_process_logfile
from config import LOG_FILE

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def should_run_fetch():
    """
    Entscheidet, ob ein Abruf durchgeführt werden soll.
    
    Zeitplan:
    - 06:00 - 01:00 Uhr: Abruf alle 15 Minuten
    - 01:00 - 06:00 Uhr: Abruf alle 30 Minuten
    """
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    
    # Nachts (01:00 - 06:00): nur bei :00 und :30
    if 1 <= hour < 6:
        return minute in [0, 30]
    
    # Tagsüber (06:00 - 01:00): alle 15 Minuten
    # :00, :15, :30, :45
    return minute in [0, 15, 30, 45]

def main():
    """Hauptfunktion."""
    if should_run_fetch():
        logger.info("Starte Abruf...")
        try:
            success = fetch_and_process_logfile()
            if success:
                logger.info("Abruf erfolgreich abgeschlossen")
            else:
                logger.warning("Abruf war nicht erfolgreich")
        except Exception as e:
            logger.error(f"Fehler beim Abruf: {e}")
    else:
        logger.debug(f"Kein Abruf erforderlich um {datetime.now().strftime('%H:%M')}")

if __name__ == "__main__":
    main()
