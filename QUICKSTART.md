# Quick Start Guide

Schnelleinstieg für das Smartmeter-Projekt

## Auf dem Raspberry Pi

### Installation (erste Ausführung)

```bash
cd /home/pi
git clone <repository-url> smartmeter_project
cd smartmeter_project

# Automatisches Setup
sudo bash setup.sh
```

Das ist alles! Das Setup-Skript macht den Rest.

### After Setup

```bash
# Service starten
sudo systemctl start smartmeter

# Im Browser öffnen
# http://muc  ← Port 80, einfach nur den Hostname!
# http://muc/sensors  ← Sensoren verwalten
```

### Optional: Netzwerk-Bridge für MUC

Falls du noch nicht während dem Setup die Bridge konfiguriert hast:

```bash
sudo bash /home/pi/smartmeter_project/network_setup.sh
sudo reboot
```

Nach dem Reboot:
```
http://muc:8080  ← Zugriff auf MUC Smartmeter (von außen)
```

---

## Entwicklung (auf deinem Computer)

```bash
# 1. Repository klonen
git clone <repository-url>
cd smartmeter_project

# 2. Virtuelle Umgebung
python3 -m venv venv
source venv/bin/activate  # oder: .\venv\Scripts\activate (Windows)

# 3. Dependencies installieren
pip install -r requirements.txt

# 4. App starten
python3 app.py

# 5. Browser: http://localhost:5000
```

---

## Wichtige Dateien

| Datei | Zweck |
|-------|-------|
| `config.py` | FTP und Flask Einstellungen |
| `db.py` | Datenbank-Modul |
| `ftp_handler.py` | FTP Download & CSV Parsing |
| `app.py` | Flask Webserver |
| `setup.sh` | Raspberry Pi Installation |

---

## Web-Seiten

- **Dashboard:** `/` - Zeigt aktuelle Daten
- **Sensoren:** `/sensors` - Sensoren verwalten
- **API Status:** `/api/status` - System-Check

---

## Cronjob Zeitplan

- **06:00 - 01:00 Uhr:** Abruf alle 15 Minuten
- **01:00 - 06:00 Uhr:** Abruf alle 30 Minuten

---

## Problembehebung

```bash
# Logs prüfen
sudo journalctl -u smartmeter -f

# Service-Status
sudo systemctl status smartmeter

# Manuelles Starten (für Debugging)
cd /home/pi/smartmeter_project
source venv/bin/activate
python3 app.py
```

Viel Spaß! 🚀
