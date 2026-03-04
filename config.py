#!/usr/bin/env python3
"""
config.py - Zentrale Konfigurationsdatei für das Smartmeter-Projekt
"""

import os

# ============ FTP-Einstellungen ============
FTP_USER = "ftp"
FTP_PASSWORD = "ftp"
SMARTMETER_IP = "192.168.100.101"
FTP_BASE_DIR = "/B:/Log"

# ============ Datenbank ============
DATABASE_FILE = os.path.join(os.path.dirname(__file__), "smartmeter.db")

# ============ Lokale Verzeichnisse ============
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# ============ Flask-Einstellungen ============
# Flask läuft intern auf Port 5000
# nginx Reverse Proxy leitet Port 80 → 5000 weiter
FLASK_HOST = "127.0.0.1"  # Nur lokal (nginx nur intern)
FLASK_PORT = 5000
FLASK_DEBUG = False

# ============ Logging ============
LOG_FILE = os.path.join(os.path.dirname(__file__), "smartmeter.log")
