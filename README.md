# Smartmeter Monitoring System

Ein modernes Temperatur- und Luftfeuchtigkeits-Monitoring-System für den Raspberry Pi mit Web-Dashboard.

## 🎯 Features

✅ **Live Dashboard** - Echtzeit-Daten mit Plotly-Diagrammen  
✅ **Dark/Light Mode** - Theme-Umschaltung mit Cookie-Speicherung  
✅ **Responsives Design** - Optimiert für Desktop & Smartphone  
✅ **Sensor-Verwaltung** - Sensoren über Web-UI hinzufügen/bearbeiten/löschen  
✅ **Automatische Datenerfassung** - Intelligenter Cronjob (15min tagsüber, 30min nachts)  
✅ **SQLite Datenbank** - Leicht und zuverlässig  
✅ **FTP-Integration** - Automatischer Abruf vom MUC-Smartmeter  
✅ **Fehlertoleranz** - Funktioniert auch wenn Datenbank beschädigt ist  
✅ **Systemd Service** - Automatischer Start beim Boot  

---

## 📦 Requirements

- **Hardware:** Raspberry Pi 3/4/5 mit Ethernet/WLAN
- **OS:** Raspberry Pi OS Bookworm (Lite oder Desktop)
- **Software:** Python 3.9+, pip, virtualenv

---

## 🚀 Installation

### 1. Repository klonen

```bash
cd /home/pi
git clone https://github.com/yourusername/smartmeter-project.git
cd smartmeter_project
```

### 2. Automatisches Setup (Empfohlen)

```bash
sudo bash setup.sh
```

Das Skript wird:
- System aktualisieren
- Python-Abhängigkeiten installieren
- Virtuelle Umgebung erstellen
- Datenbank initialisieren
- Cronjob einrichten
- Systemd Service konfigurieren

### 3. Manuelles Setup

Falls du das Setup-Skript nicht verwenden möchtest:

```bash
# Virtuelle Umgebung erstellen
python3 -m venv venv
source venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# Datenbank initialisieren
python3 -c "from db import _create_database; _create_database()"

# Service starten
python3 app.py
```

---

## ⚙️ Konfiguration

Bearbeite `config.py` um die Einstellungen anzupassen:

```python
# FTP-Einstellungen
FTP_USER = "ftp"
FTP_PASSWORD = "ftp"
SMARTMETER_IP = "192.168.100.101"

# Flask
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = False
```

---

## 🌐 Zugriff

Nachdem der Service gestartet ist:

Nachdem der Service gestartet ist:

- **Web-Interface Dashboard:** `http://muc` (Port 80 über nginx)
- **Sensor-Verwaltung:** `http://muc/sensors`
- **MUC Smartmeter:** `http://muc:8080` (Portweiterleitung von außen) oder `http://192.168.100.101` (direkt im LAN)
- **API Status:** `http://muc/api/status`

---

## 📊 Datenerfassung - Zeitplan

| Zeitfenster | Intervall |
|-------------|-----------|
| **06:00 - 01:00** | Alle 15 Minuten |
| **01:00 - 06:00** | Alle 30 Minuten |

Der Cronjob läuft **jede Minute** und entscheidet anhand der Uhrzeit, ob ein Abruf erfolgt.

---

## 📱 Bedienung

### Dashboard
- Zeigt aktuelle Messwerte aller Sensoren
- Interactive Diagramme (1h, 1d, 7d, 30d)
- Automatisches Refresh der Daten

### Sensoren verwalten
- **Hinzufügen:** Device ID + Name eingeben
- **Bearbeiten:** Sensor-Name ändern
- **Löschen:** Sensor + alle Daten entfernen

---

## 🛠️ Verwaltung

### Service starten/stoppen

```bash
# Starten
sudo systemctl start smartmeter

# Stoppen
sudo systemctl stop smartmeter

# Status prüfen
sudo systemctl status smartmeter

# Beim Boot automatisch starten
sudo systemctl enable smartmeter
```

### Logs anschauen

```bash
# Systemd logs
sudo journalctl -u smartmeter -f

# Anwendungs-Logs
tail -f /home/pi/smartmeter_project/smartmeter.log
```

### Manueller Datenimport

Zur initialen Befüllung der Datenbank mit historischen Daten:

```bash
sudo /home/pi/smartmeter_project/manual_import.sh
```

Dieses Skript lädt **alle** historischen Logdateien vom MUC herunter.

---

## 📁 Projektstruktur

```
smartmeter_project/
├── app.py                    # Flask Hauptanwendung
├── config.py                 # Konfiguration
├── db.py                     # Datenbank-Modul
├── ftp_handler.py            # FTP und CSV-Import
├── cronjob_fetch.py          # Abruf-Logik
├── cronjob_wrapper.sh        # Cronjob-Wrapper
├── manual_import.sh          # Manueller Import
├── setup.sh                  # Installations-Skript
├── requirements.txt          # Python-Abhängigkeiten
├── smartmeter.service        # Systemd Service
├── static/
│   ├── css/style.css        # Bootstrap + Custom Styles
│   └── js/theme.js          # Dark/Light Mode
├── templates/
│   ├── base.html            # Base Template
│   ├── index.html           # Dashboard
│   ├── sensors.html         # Sensor-Verwaltung
│   └── error.html           # Error Page
├── logs/                     # Temporäre CSV-Dateien
└── smartmeter.db            # SQLite Datenbank
```

---

## 🐛 Troubleshooting

### "Datenbankfehler"
```bash
# Datenbank neu initialisieren
rm /home/pi/smartmeter_project/smartmeter.db
python3 /home/pi/smartmeter_project/app.py
```

### "FTP-Verbindungsfehler"
- Prüfe IP-Adresse und Credentials in `config.py`
- Teste Verbindung: `ftp <SMARTMETER_IP>`
- Prüfe Netzwerk: `ping 192.168.100.101`

### "Keine Sensoren konfiguriert"
- Öffne `/sensors` um Sensoren hinzuzufügen
- Device ID muss exakt entsprechen (z.B. `WEP-00004606-02-27`)

### "Web-Interface nicht erreichbar"
```bash
# Service Status prüfen
sudo systemctl status smartmeter

# Logs prüfen
sudo journalctl -u smartmeter -n 50
```

---

## 📝 API-Endpoints

| Method | Endpoint | Beschreibung |
|--------|----------|-------------|
| GET | `/` | Dashboard |
| GET | `/sensors` | Sensoren-Verwaltung |
| POST | `/api/sensor/add` | Sensor hinzufügen |
| POST | `/api/sensor/update` | Sensor aktualisieren |
| DELETE | `/api/sensor/delete/<id>` | Sensor löschen |
| GET | `/api/status` | System-Status |

---

## 🔄 Systemd Service

Die `smartmeter.service` startet die Flask-App automatisch:

```bash
# Service installieren
sudo cp smartmeter.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable smartmeter
sudo systemctl start smartmeter
```

---

## 📘 Developer Info

### Virtuelle Umgebung aktivieren

```bash
source venv/bin/activate
```

### App lokal starten

```bash
python3 app.py
```

### Tests

```bash
python3 -m pytest
```

### Code-Stil

```bash
pip install black flake8
black *.py
```

---

## 🤝 Lizenz

MIT License - Siehe LICENSE für Details

---

## 📞 Support

Bei Problemen:
1. Logs prüfen: `tail -f smartmeter.log`
2. Datenbank-Status: Öffne `/api/status`
3. GitHub Issues: Link zum Projekt

---

**Viel Erfolg mit dem Smartmeter Monitoring System!** 🎉
