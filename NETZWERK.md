# Netzwerk-Architektur - Smartmeter Projekt

## Übersicht

```
     Hauptnetzwerk (z.B. Home WiFi 192.168.1.0/24)
            |
            | WiFi Interface (z.B. wlan0)
            |
     ┌──────────────────────────────────────┐
     │     Raspberry Pi Bookworm            │
     │     Hostname: muc                    │
     │     192.168.1.x (DHCP vom Router)    │
     │                                      │
     │  ┌─ nginx (Port 80)                  │
     │  │  └─> Flask (Port 5000 intern)    │
     │  │                                   │
     │  └─ Port Forwarding 8080→MUC:502   │
     │                                      │
     │  Ethernet LAN Bridge                │
     │  192.168.100.1/24                   │
     └──────────────────────────────────────┘
            |
            | Ethernet (eth0)
            | Bridge zum MUC
            |
     ┌──────────────────────────────────────┐
     │     MUC Smartmeter                   │
     │     192.168.100.101                  │
     │     Port 502 (HTTP)                  │
     └──────────────────────────────────────┘
```

---

## Netzwerk-Interfaces

### WiFi (wlan0)
- **Zweck:** Verbindung zum Hauptnetzwerk
- **IP:** DHCP vom Router (z.B. 192.168.1.50)
- **Funktion:** Internet-Zugang, Remote-Zugriff

### Ethernet (eth0)
- **Zweck:** Bridge zum MUC Smartmeter
- **IP:** 192.168.100.1/24 (statisch)
- **Hostgruppe:** 192.168.100.0/24
  - 192.168.100.1 = Raspberry Pi
  - 192.168.100.101 = MUC Smartmeter

---

## Zugriff auf das System

### 1. Smartmeter Dashboard (Web-Interface)

**Von überall im Netzwerk:**
```
http://muc                     ← Einfach nur "muc" eingeben!
http://muc/sensors             ← Sensor-Verwaltung
http://muc/api/status          ← Status prüfen
```

**Oder mit IP direkt:**
```
http://192.168.1.x:80          ← WiFi IP (falls muc nicht auflöst)
```

### 2. MUC Smartmeter (externe Ports)

**Von außen (Portweiterleitung):**
```
http://muc:8080                ← MUC über Portweiterleitung
```

**Direkt im lokalen MUC-LAN:**
```
http://192.168.100.101         ← Direkt am MUC
http://192.168.100.101:502     ← Mit Port (falls nötig)
```

**Vom Raspberry Pi selbst:**
```
ssh pi@muc
# Oder
ssh pi@192.168.1.x
```

---

## Konfigurationsdateien

### /etc/dhcpcd.conf (nach Netzwerk-Setup)
```ini
interface wlan0
# DHCP vom Router

interface eth0
static ip_address=192.168.100.1/24
static routers=192.168.100.254
static domain_name_servers=8.8.8.8 8.8.4.4
```

### /etc/hostname
```
muc
```

### /etc/hosts
```
127.0.0.1    localhost
::1          localhost
127.0.1.1    muc
```

### iptables (Port Forwarding)
```bash
# Port 8080 → MUC:502
iptables -t nat -A PREROUTING -p tcp --dport 8080 \
  -j DNAT --to-destination 192.168.100.101:502
```

### /etc/nginx/sites-available/smartmeter
```nginx
server {
    listen 80;
    server_name muc localhost;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
    }
    
    location /static/ {
        alias /home/pi/smartmeter_project/static/;
    }
}
```

---

## Installation der Bridge

Die Netzwerk-Bridge wird während des `setup.sh` automatisch konfiguriert oder kann manuell ausgeführt werden:

```bash
sudo bash /home/pi/smartmeter_project/network_setup.sh
```

Das Skript:
1. ✅ Setzt Hostname auf "muc"
2. ✅ Konfiguriert DHCP für WiFi
3. ✅ Setzt statische IP für Ethernet (192.168.100.1)
4. ✅ Aktiviert IP Forwarding
5. ✅ Konfiguriert iptables für Weiterleitung
6. ✅ Speichert iptables persistently
7. ✅ Der Reboot wird empfohlen

---

## Testen der Verbindung

### 1. Hostname auflösen
```bash
ping muc
# Sollte 192.168.1.x zurückgeben (WiFi IP)
```

### 2. MUC erreichbar?
```bash
ping 192.168.100.101
# Sollte erfolgreich sein
```

### 3. Web-Interface
```bash
curl http://muc
# Sollte HTML zurückgeben
```

### 4. MUC über Portweiterleitung
```bash
curl http://muc:8080
# Sollte MUC-Seite zurückgeben
```

### 5. Netzwerk-Info
```bash
ip addr                    # Interface-IPs
ip route                   # Routing-Tabelle
iptables -L -n -t nat      # NAT-Regeln
systemctl status nginx      # nginx Status
```

---

## Netzwerk-Routing

```
Paket zu http://muc:8080 (extern)
  ↓
  iptables PREROUTING-Regel:
  Port 8080 → 192.168.100.101:502
  ↓
  Forwarding eth0 → 192.168.100.101
  ↓
  Response zurück
  ↓
  iptables POSTROUTING:
  MASQUERADE (als 192.168.100.1 erscheinen)
  ↓
  Zurück zum Client
```

---

## Fehlerbehandlung

### "muc" wird nicht aufgelöst
```bash
# Prüfe /etc/hostname und /etc/hosts
cat /etc/hostname   # Sollte "muc" sein
cat /etc/hosts      # Sollte 127.0.1.1 muc enthalten

# systemd-resolved Check
systemctl restart systemd-resolved
```

### Keine Verbindung zu MUC (192.168.100.101)
```bash
# Ethernet-Kabel prüfen
ip link show eth0        # UP?
ip addr show eth0        # 192.168.100.1?
ping 192.168.100.1       # Local Loopback

# Routing prüfen
ip route show           # 192.168.100.0/24 via eth0?

# iptables Regeln
iptables -L -n -v       # Forwarding rules?
```

### nginx nicht erreichbar auf Port 80
```bash
sudo systemctl status nginx              # Running?
sudo netstat -tlnp | grep :80           # Port offen?
sudo nginx -t                           # Config ok?
sudo tail -f /var/log/nginx/error.log   # Errors?
```

### Port 8080 funktioniert nicht
```bash
# iptables Regeln Check
sudo iptables-save | grep 8080

# NAT Regeln in Detail
sudo iptables -t nat -L -v -n

# Forward Rules
sudo iptables -L -v -n
```

---

## Weitere Infos

### DNS
```bash
# Primary DNS (8.8.8.8 Google)
# Fallback (1.1.1.1 Cloudflare)
cat /etc/systemd/resolved.conf.d/muc.conf
```

### WLAN Verbindung
Die WiFi-Verbindung wird automatisch via DHCP vom Router konfiguriert:
```bash
nmtui          # Network Manager UI
iwconfig       # WLAN-Info
```

### Statische Routen (optional)
Falls externe Geräte spezielle Routen zum MUC benötigen:
```bash
ip route add 192.168.100.0/24 via <raspberry_pi_ip>
```

---

## Production-Tipps

1. **UPnP/IGMP deaktivieren** (Sicherheit)
   ```bash
   echo "net.ipv4.conf.all.send_redirects = 0" | sudo tee -a /etc/sysctl.conf
   ```

2. **Firewall** (optional)
   ```bash
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   sudo ufw allow 22/tcp   # SSH
   sudo ufw allow 80/tcp   # HTTP
   sudo ufw allow 8080/tcp # MUC Port
   sudo ufw enable
   ```

3. **Monitoring**
   ```bash
   watch -n 1 'ip link show; echo "---"; ping -c 1 192.168.100.101'
   ```

---

Viel Erfolg! 🚀
