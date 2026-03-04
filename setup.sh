#!/bin/bash
################################################################################
# setup.sh - Installation und Konfiguration für Raspberry Pi
#
# Dieses Skript installiert alle Abhängigkeiten und konfiguriert das System
# für die Ausführung des Smartmeter-Projekts auf Raspberry Pi Bookworm.
#
# Verwendung: sudo bash setup.sh
################################################################################

set -e  # Exit bei Fehler

echo "================================================================"
echo "Smartmeter Projekt - Raspberry Pi Setup"
echo "================================================================"
echo ""

# Farben für Ausgabe
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Funktionen
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Prüfe root-Rechte
if [ "$EUID" -ne 0 ]; then 
    log_error "Dieses Skript muss mit sudo ausgeführt werden!"
    exit 1
fi

# 2. System aktualisieren
log_info "Aktualisiere System..."
apt-get update
apt-get upgrade -y

# 3. Installiere erforderliche Pakete
log_info "Installiere erforderliche Pakete..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    sqlite3 \
    curl \
    wget \
    nginx \
    iptables-persistent \
    network-manager \
    dhcpcd5

# 4. Projektverzeichnis
PROJECT_DIR="/home/pi/smartmeter_project"
log_info "Erstelle Projektverzeichnis: $PROJECT_DIR"

if [ ! -d "$PROJECT_DIR" ]; then
    mkdir -p "$PROJECT_DIR"
    log_info "Verzeichnis erstellt"
else
    log_warn "Verzeichnis existiert bereits"
fi

# 5. Virtuelle Python-Umgebung
log_info "Erstelle virtuelle Python-Umgebung..."
if [ ! -d "$PROJECT_DIR/venv" ]; then
    python3 -m venv "$PROJECT_DIR/venv"
    log_info "Virtuelle Umgebung erstellt"
else
    log_warn "Virtuelle Umgebung existiert bereits"
fi

# 6. Aktiviere virtuelle Umgebung und installiere Dependencies
log_info "Installiere Python-Abhängigkeiten..."
source "$PROJECT_DIR/venv/bin/activate"
pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt"

# 7. Initialisiere Datenbank
log_info "Initialisiere Datenbank..."
python3 "$PROJECT_DIR/db.py" << 'PYTHON_INIT'
import sys
sys.path.insert(0, '/home/pi/smartmeter_project')
from db import db_health_check
success, message = db_health_check()
print(f"Datenbank Status: {message}")
PYTHON_INIT

# 8. Setze Dateiberechtigungen
log_info "Setze Dateiberechtigungen..."
chown -R pi:pi "$PROJECT_DIR"
chmod +x "$PROJECT_DIR/cronjob_wrapper.sh"
chmod +x "$PROJECT_DIR/manual_import.sh"
chmod +x "$PROJECT_DIR/app.py"

# 9. Systemd Service (optional)
log_info "Erstelle systemd Service..."
cat > /etc/systemd/system/smartmeter.service << 'SYSTEMD_SERVICE'
[Unit]
Description=Smartmeter Flask Application
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/smartmeter_project
ExecStart=/home/pi/smartmeter_project/venv/bin/python /home/pi/smartmeter_project/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SYSTEMD_SERVICE

systemctl daemon-reload
log_info "Systemd Service installiert"

# 10. Cronjob einrichten
log_info "Richte Cronjob ein..."
# Entferne alter Cronjob falls vorhanden
crontab -u pi -l 2>/dev/null | grep -v "cronjob_wrapper.sh" | crontab -u pi - || true

# Neuer Cronjob: Jede Minute prüfen
CRON_JOB="* * * * * /home/pi/smartmeter_project/cronjob_wrapper.sh"
(crontab -u pi -l 2>/dev/null; echo "$CRON_JOB") | crontab -u pi -

log_info "Cronjob eingerichtet (jede Minute)"

# 11. Nginx Konfigurieren (Reverse Proxy für Port 80)
log_info "Konfiguriere nginx als Reverse Proxy..."

# Alte Standard Config löschen
rm -f /etc/nginx/sites-enabled/default

# Neue Config kopieren
cp "$PROJECT_DIR/smartmeter_nginx.conf" /etc/nginx/sites-available/smartmeter
ln -sf /etc/nginx/sites-available/smartmeter /etc/nginx/sites-enabled/smartmeter

# Nginx testen
if nginx -t >/dev/null 2>&1; then
    log_info "Nginx Konfiguration OK"
    systemctl enable nginx
    systemctl restart nginx
    log_info "Nginx gestartet und aktiviert"
else
    log_error "Nginx Konfiguration fehlerhaft!"
    exit 1
fi

# 12. Netzwerk-Bridge Setup (optional)
log_info ""
log_info "Netzwerk-Bridge Konfiguration"
log_info "================================"
echo ""
echo "Dieses Skript unterstützt automatisch:"
echo "  • NetworkManager (moderne Raspberry Pi OS Bookworm)"
echo "  • dhcpcd (ältere Varianten)"
echo ""
read -p "Soll die Netzwerk-Bridge (WiFi ↔ LAN zum MUC) konfiguriert werden? (j/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Jj]$ ]]; then
    log_info "Starte Netzwerk-Bridge Setup (Auto-Detection aktiv)..."
    chmod +x "$PROJECT_DIR/network_setup.sh"
    bash "$PROJECT_DIR/network_setup.sh"
    
    echo ""
    log_warn "⚠️  Reboot erforderlich für Netzwerk-Änderungen!"
    echo ""
    read -p "Jetzt neustarten? (j/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Jj]$ ]]; then
        log_info "System wird neu gestartet..."
        sleep 2
        reboot
    else
        log_warn "Bitte später manuell neustarten: sudo reboot"
    fi
else
    log_info "Netzwerk-Bridge Setup übersprungen"
    log_info "Kann später manuell ausgeführt werden: sudo bash network_setup.sh"
fi

# 13. Startmöglichkeiten
echo ""
echo "================================================================"
echo -e "${GREEN}Setup abgeschlossen!${NC}"
echo "================================================================"
echo ""
echo "🚀 VERWENDUNG:"
echo ""
echo "  Web-Interface:"
echo "    http://muc         (Port 80 - über nginx)"
echo "    http://localhost   (lokal)"
echo ""
echo "  MUC Smartmeter (wenn Bridge konfiguriert):"
echo "    http://muc:8080    (Portweiterleitung extern)"
echo "    http://192.168.100.101 (direkt im LAN)"
echo ""
echo "  Service-Befehle:"
echo "    sudo systemctl start smartmeter      # Starten"
echo "    sudo systemctl stop smartmeter       # Stoppen"
echo "    sudo systemctl restart smartmeter    # Neustarten"
echo "    sudo systemctl enable smartmeter     # Beim Boot starten"
echo "    sudo systemctl status smartmeter     # Status anzeigen"
echo ""
echo "  Logs anschauen:"
echo "    sudo journalctl -u smartmeter -f"
echo "    sudo tail -f /var/log/nginx/smartmeter_access.log"
echo "    tail -f /home/pi/smartmeter_project/smartmeter.log"
echo ""
echo "  Sensoren verwalten:"
echo "    → Web-Browser: http://muc/sensors"
echo ""
echo "  Manueller Datenimport (einmalig, optional):"
echo "    /home/pi/smartmeter_project/manual_import.sh"
echo ""
echo "  Netzwerk-Bridge nachträglich konfigurieren:"
echo "    sudo bash /home/pi/smartmeter_project/network_setup.sh"
echo ""
echo "  Manueller Start (für Debugging):"
echo "    cd /home/pi/smartmeter_project"
echo "    source venv/bin/activate"
echo "    python3 app.py"
echo ""
echo "================================================================"
echo -e "${GREEN}✅ Smartmeter ist bereit!${NC}"
echo "================================================================"
