# Projektübersicht - Smartmeter Monitoring System

## 🎯 Was wurde erstellt

Ein **vollständig funktionierendes Smartmeter Monitoring System** für Raspberry Pi mit:

- ✅ Modernes Web-Interface mit Bootstrap 5
- ✅ Dark/Light Mode Toggle (Cookie-basiert)
- ✅ Responsive Design (Desktop & Mobile)
- ✅ Web-basierte Sensor-Verwaltung
- ✅ Automatische Datenerfassung mit intelligenter Zeitsteuerung
- ✅ Fehlerbehandlung für Datenbankprobleme
- ✅ Systemd Service für automatischen Start
- ✅ Komplettes Setup-Skript für Raspberry Pi
- ✅ **nginx Reverse Proxy (Port 80)** - http://muc (ohne Port-Angabe!)
- ✅ **WiFi ↔ LAN Bridge zum MUC** - Automatische Konfiguration
- ✅ **Port Forwarding** - Port 8080 → MUC (extern erreichbar)

---

## 📋 Datei-Übersicht

### Python-Module

```
app.py                  - Flask Webserver mit REST API
config.py              - Zentrale Konfiguration (FTP, Flask)
db.py                  - SQLite Datenbank mit Fehlerbehandlung
ftp_handler.py         - FTP-Verbindung und CSV-Parsing
cronjob_fetch.py       - Intelligente Abruf-Logik (15min/30min)
init_db.py             - Datenbank-Initialisierungsskript
```

### Web-Interface

```
templates/base.html     - Base Template mit Navigation
templates/index.html    - Dashboard mit Plotly-Diagrammen
templates/sensors.html  - Sensor-Verwaltungsseite
templates/error.html    - Error Page

static/css/style.css   - Bootstrap + Custom Styles
static/js/theme.js     - Dark/Light Mode Toggle
```

### Scripts & Konfiguration

```
setup.sh               - Automatisches Installation auf Raspberry Pi
network_setup.sh       - WiFi↔LAN Bridge Konfiguration (automatisch oder manuell)
cronjob_wrapper.sh     - Cronjob für Python-Ausführung
manual_import.sh       - Manueller Import historischer Daten
smartmeter.service     - Systemd Service Definition
smartmeter_nginx.conf  - nginx Reverse Proxy Konfiguration
requirements.txt       - Python-Abhängigkeiten
```

### Dokumentation

```
README.md              - Ausführliche Dokumentation
QUICKSTART.md          - Schnelleinstieg
DOCS.md                - Unterstützungs-Infos
PROJECTINFO.md         - Diese Datei
```

---

## 🚀 Verwendung auf Raspberry Pi

### 1️⃣ Installation

```bash
# Repository klonen
git clone <your-repo> ~/smartmeter_project
cd ~/smartmeter_project

# Automatisches Setup
sudo bash setup.sh
```

Das Setup skript installiert automatisch:
- System-Updates
- Python 3 + pip
- Virtuelle Umgebung
- Alle Abhängigkeiten
- Datenbank
- Cronjob
- Systemd Service

### 2️⃣ Service starten

```bash
# Starten
sudo systemctl start smartmeter

# Logs prüfen
sudo journalctl -u smartmeter -f

# Im Browser öffnen
# http://<raspberry-pi-ip>:5000
```

### 3️⃣ Sensoren hinzufügen

- Öffne `http://<raspberry-pi-ip>:5000/sensors`
- Device ID eintragen (z.B. `WEP-00004606-02-27`)
- Sensor-Name eingeben
- Absenden

### 4️⃣ Daten importieren (optional)

```bash
# Historische Daten vom MUC importieren
bash ~/smartmeter_project/manual_import.sh
```

---

## 🔄 Automatische Datenerfassung

Der Cronjob läuft **jede Minute** und entscheidet automatisch:

| Zeit | Abruf |
|------|-------|
| 06:00 - 01:00 Uhr | Alle 15 Minuten ✓ |
| 01:00 - 06:00 Uhr | Alle 30 Minuten ✓ |

**Logik in:** `cronjob_fetch.py`

---

## 📊 Web-Interface Features

### Dashboard (/)
- 📊 Live-Diagramme mit Plotly
- 🌡️ Aktuelle Messwerte (Temp & Luftfeuchtigkeit)
- ⏱️ Letzter Update-Zeitstempel
- 📱 Responsive auf mobilen Geräten
- 🎨 Dark/Light Mode
- 📈 Zeitraum-Auswahl (1h, 1d, 7d, 30d)

### Sensoren (/sensors)
- ➕ Neuen Sensor hinzufügen
- ✏️ Sensor umbenennen
- 🗑️ Sensor löschen
- 📋 Auflistung aller Sensoren

### API (/api/*)
- `/api/status` - System-Status
- `/api/sensor/add` - POST
- `/api/sensor/update` - POST
- `/api/sensor/delete/<id>` - DELETE

---

## 🛠️ Konfiguration

**Datei:** `config.py`

```python
# FTP zum Smartmeter
FTP_USER = "ftp"
FTP_PASSWORD = "ftp"
SMARTMETER_IP = "192.168.100.101"

# Flask Webserver
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
```

---

## 📝 Datenbank-Schema

```sql
-- Sensoren
CREATE TABLE sensors (
    id INTEGER PRIMARY KEY,
    device_id TEXT UNIQUE,
    sensor_name TEXT
);

-- Messungen
CREATE TABLE measurements (
    id INTEGER PRIMARY KEY,
    device_id TEXT,
    timestamp INTEGER,
    temperature REAL,
    humidity REAL,
    FOREIGN KEY(device_id) REFERENCES sensors(device_id)
);
```

---

## ⚡ Performance & Optimierungen

- ✅ **Indexierung:** DB-Indizes für schnelle Abfragen
- ✅ **Caching:** Daten in Sessions gecacht
- ✅ **Responsive:** Minimale CSS/JS Dateigröße
- ✅ **Mobile First:** Bootstrap responsive Grid
- ✅ **Error Handling:** Graceful degradation
- ✅ **Logging:** Alle Aktionen geloggt

---

## 🐛 Fehlerbehandlung

Die Anwendung funktioniert auch wenn:
- 🛑 Datenbank korrupt: Fehlerseite wird angezeigt
- 🛑 FTP nicht erreichbar: Error-Log wird geschrieben
- 🛑 Sensor offline: Letzte bekannte Werte bleiben sichtbar

---

## 📱 Responsive Design

```
Desktop (>992px)    - 3 Diagramme nebeneinander
Tablet (768-991px)  - 2 Diagramme
Mobile (<768px)     - 1 Diagramm
```

---

## 🎨 Design-Features

- **Bootstrap 5.3.0** - Modernes CSS Framework
- **Bootstrap Icons** - 2000+ Icons
- **Plotly.js** - Interactive Charts
- **Dark Mode** - Mit Cookie-Speicherung
- **Responsive Grid** - Flexbox Layout

---

## 📦 Abhängigkeiten

```
Flask==3.0.0
Werkzeug==3.0.1
Jinja2==3.1.2
click==8.1.7
```

Keine externen Python-Datenbank-Treiber nötig (SQLite builtin)!

---

## 🚢 Deployment

### Raspberry Pi (Production)
```bash
sudo bash setup.sh
sudo systemctl enable smartmeter
sudo systemctl start smartmeter
```

### Lokal (Development)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

---

## 📊 Vergleich: Alt vs. Neu

| Feature | Alt | Neu |
|---------|-----|-----|
| Design | Basic | Modern Bootstrap 5 |
| Dark Mode | ❌ | ✅ |
| Mobile | ❌ | ✅ |
| Sensor-Verwaltung | CLI | Web-UI |
| Error Handling | Basic | Robust |
| Service | ❌ | systemd ✅ |
| Setup | Manual | Automatisch ✓ |

---

## 🎓 Lern-Ressourcen

- `README.md` - Ausführliche Dokumentation
- `QUICKSTART.md` - Schnelleinstieg
- `config.py` - Kommentierte Konfiguration
- `db.py` - DB-Patterns
- `ftp_handler.py` - FTP-Integration
- `app.py` - Flask Patterns

---

## ✅ Checkliste für Production

- [ ] `config.py` - Werte korrekt?
- [ ] `setup.sh` - Auf Pi ausgeführt?
- [ ] Service aktiv: `sudo systemctl status smartmeter`
- [ ] Web-Interface erreichbar?
- [ ] Sensoren konfiguriert?
- [ ] Logs prüfen: `journalctl -u smartmeter`
- [ ] Cronajob aktiv: `crontab -u pi -l`
- [ ] Datenbank gespeichert: `ls -la *.db`

---

## 📞 Support & Troubleshooting

```bash
# 1. Service Check
sudo systemctl status smartmeter

# 2. Logs Live
sudo journalctl -u smartmeter -f

# 3. Manuelle Ausführung (Debug)
cd /home/pi/smartmeter_project
source venv/bin/activate
python3 app.py

# 4. Datenbank Check
python3 -c "from db import db_health_check; print(db_health_check())"

# 5. FTP Test
ftp 192.168.100.101
```

---

## 🎉 Fertig!

Das Projekt ist einsatzbereit. Viel Erfolg! 🚀
