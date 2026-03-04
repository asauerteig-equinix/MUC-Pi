# Netzwerk-Features - Zusammenfassung

## 🎯 Was wurde hinzugefügt

Dein Smartmeter-Projekt wurde um professionelle Netzwerk-Features erweitert:

### 1️⃣ nginx Reverse Proxy (Port 80)
- ✅ **Einfacher Zugriff:** `http://muc` (ohne Port-Angabe!)
- ✅ **Statt:** `http://192.168.1.x:5000`
- ✅ **Auch:** `http://localhost` auf dem Pi selbst
- ✅ **nginx** läuft auf Port 80, leitet zu Flask (Port 5000) weiter

### 2️⃣ WiFi ↔ LAN Bridge (Netzwerk-Setup)
- ✅ **Verbindung zweier Netzwerke:**
  - WiFi: Hauptnetzwerk (Router → DHCP)
  - LAN: MUC Smartmeter (192.168.100.1/24 → Statisch)
  
- ✅ **Pi hat Namen:** `muc` (auflösbar als `ping muc`)

- ✅ **Automatische Setup:** `network_setup.sh` konfiguriert alles

### 3️⃣ Port Forwarding (8080 → MUC)
- ✅ **Zugriff auf MUC von extern:** `http://muc:8080`
- ✅ **Oder lokal direkt:** `http://192.168.100.101`
- ✅ **iptables** Regeln für NAT & Port-Weiterleitung

---

## 📂 Neue/Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `config.py` | Flask nur auf 127.0.0.1:5000 (lokal) |
| `setup.sh` | ✅ nginx Installation & Konfiguration |
| `setup.sh` | ✅ network_setup.sh Integrationen |
| `smartmeter_nginx.conf` | ✨ Neu: nginx Konfiguration |
| `network_setup.sh` | ✨ Neu: Bridge-Setup Skript |
| `NETZWERK.md` | ✨ Neu: Vollständige Netzwerk-Doku |
| `README.md` | ✅ URLs aktualisiert |
| `QUICKSTART.md` | ✅ URLs aktualisiert |
| `PROJECTINFO.md` | ✅ Features aktualisiert |

---

## 🚀 Installation

### Automatisch (Empfohlen)
```bash
sudo bash setup.sh
# Bei Frage: "Netzwerk-Bridge konfigurieren?" → JA eingeben
# Das war's! Reboot lädt die neuen Konfigurationen.
```

### Manuell später
```bash
sudo bash /home/pi/smartmeter_project/network_setup.sh
sudo reboot
```

---

## 🌐 Nach der Installation

### Zugriff von überall im Netzwerk:
```
http://muc              ← Smartmeter Dashboard
http://muc/sensors      ← Sensor-Verwaltung
http://muc:8080         ← MUC Smartmeter (extern)
```

### Im Browser musst du einfach eingeben:
- **Hostname:** `muc`
- **Keine Port-Angabe nötig!** (nginx läuft auf Standard-Port 80)

### Das funktioniert auch unterwegs:
- Wenn du von außerhalb Zugriff auf MUC brauchst:
  - `http://muc:8080` (Port 8080 wird zum MUC weitergeleitet)

---

## ⚙️ Technische Details

### Netzwerk-Architektur
```
Hauptnetzwerk (WiFi)  ← → Raspberry Pi (eth0 + wlan0) ← → MUC LAN (192.168.100.0/24)
```

### Was das `network_setup.sh` macht:
1. ✅ Hostname auf "muc" setzen
2. ✅ Ethernet auf statische IP (192.168.100.1) konfigurieren
3. ✅ WiFi auf DHCP (vom Router) konfigurieren
4. ✅ IP Forwarding aktivieren
5. ✅ iptables für NAT einrichten
6. ✅ Port 8080 → MUC:502 Weiterleitung
7. ✅ iptables Regeln persistent speichern

### nginx macht:
- Port 80 abhören
- Anfragen zu `http://muc` entgegennehmen
- Intern zu Flask (Port 5000) weiterleiten
- Statische Dateien direkt servieren

---

## 🔍 Testen der Umgebung

```bash
# 1. Hostname prüfen
hostname                    # Sollte: muc

# 2. Netzwerk-Interfaces
ip addr                     # eth0 und wlan0 sichtbar?

# 3. MUC erreichbar?
ping 192.168.100.101       # Antwort?

# 4. Web-Interface
curl http://muc            # HTML zurückgeben?

# 5. nginx Status
sudo systemctl status nginx # Running?

# 6. iptables Regeln
sudo iptables -L -n -t nat  # 8080→502 Regel sichtbar?
```

---

## 📖 Dokumentation

- **NETZWERK.md** - Ausführliche Netzwerk-Dokumentation
- **README.md** - Gesamtübersicht (aktualisiert)
- **QUICKSTART.md** - Quick Start (aktualisiert)

---

## ⚡ Tipps & Tricks

### Schnell DNS updaten (falls "muc" nicht auflöst)
```bash
sudo systemctl restart systemd-resolved
```

### nginx Logs ansehen
```bash
sudo tail -f /var/log/nginx/smartmeter_access.log
sudo tail -f /var/log/nginx/smartmeter_error.log
```

### iptables Regeln persistently speichern
```bash
sudo iptables-save > /etc/iptables/rules.v4
sudo systemctl enable netfilter-persistent
```

### Netzwerk-Bridge deaktivieren (falls Problem)
```bash
sudo bash /home/pi/smartmeter_project/network_setup.sh
# Wähle: Nein
```

---

## 🎉 Fertig!

Das System ist jetzt produktionsreif. Du kannst:

1. ✅ Von überall im Netzwerk auf Smartmeter-Dashboard zugreifen
2. ✅ Einfach `http://muc` in den Browser eingeben
3. ✅ Extern auf MUC zugreifen über Port 8080
4. ✅ Alles automatisch konfiguriert beim Setup

Viel Erfolg! 🚀
