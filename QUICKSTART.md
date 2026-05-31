# Quick Start Guide

Schnelleinstieg fuer das Smartmeter/MUC-Pi-Projekt.

## Auf dem Raspberry Pi

### Installation auf einem neuen System

```bash
cd /home/pi
git clone https://github.com/asauerteig-equinix/MUC-Pi.git
cd MUC-Pi

# Automatisches Setup
sudo bash setup.sh
```

Das Setup-Skript erkennt den aktuellen Projektordner automatisch und richtet
systemd, nginx und cron passend dazu ein.

### Bestehende Installation aktualisieren

Die Datenbank bleibt lokal im jeweiligen Projektordner und wird von Git ignoriert.
Vor dem ersten Update trotzdem einmal sichern:

```bash
cd /home/pi/smartmeter_project  # alte Installation
# oder:
cd /home/pi/MUC-Pi              # neue Installation

cp smartmeter.db smartmeter.db.backup-before-update
git status
git pull
sudo bash setup.sh
sudo systemctl restart smartmeter
```

Lokale Daten wie `smartmeter.db`, `smartmeter.log`, `logs/` und `venv/` werden
nicht geloescht.

### After Setup

```bash
# Service starten
sudo systemctl start smartmeter

# Im Browser oeffnen
# http://muc
# http://muc/sensors
```

### Optional: Netzwerk-Bridge fuer MUC

Falls du noch nicht waehrend dem Setup die Bridge konfiguriert hast:

```bash
sudo bash ./network_setup.sh
sudo reboot
```

Nach dem Reboot:

```text
http://muc:8080
```

---

## Entwicklung auf deinem Computer

```bash
# 1. Repository klonen
git clone https://github.com/asauerteig-equinix/MUC-Pi.git
cd MUC-Pi

# 2. Virtuelle Umgebung
python3 -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate

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
| `ftp_handler.py` | FTP Download und CSV Parsing |
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
# Logs pruefen
sudo journalctl -u smartmeter -f

# Service-Status
sudo systemctl status smartmeter

# Manuelles Starten im jeweiligen Projektordner
cd /home/pi/MUC-Pi
source venv/bin/activate
python3 app.py
```
