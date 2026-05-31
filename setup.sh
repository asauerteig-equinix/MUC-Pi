#!/bin/bash
################################################################################
# setup.sh - Installation und Konfiguration fuer Raspberry Pi
#
# Dieses Skript installiert alle Abhaengigkeiten und konfiguriert das System
# fuer die Ausfuehrung des Smartmeter/MUC-Pi-Projekts auf Raspberry Pi OS.
#
# Verwendung:
#   sudo bash setup.sh
#
# Bestehende Daten bleiben erhalten:
# - Keine Projektordner werden umbenannt oder verschoben.
# - smartmeter.db, logs/ und venv/ werden nicht geloescht.
# - systemd, nginx und cron werden auf den aktuellen Projektpfad gesetzt.
################################################################################

set -euo pipefail

echo "================================================================"
echo "Smartmeter / MUC-Pi - Raspberry Pi Setup"
echo "================================================================"
echo ""

# Farben fuer Ausgabe
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

require_file() {
    local file_path="$1"
    if [ ! -f "$file_path" ]; then
        log_error "Erforderliche Datei fehlt: $file_path"
        log_error "Bitte setup.sh aus dem geklonten Projektordner starten."
        exit 1
    fi
}

# 1. Pruefe root-Rechte
if [ "$EUID" -ne 0 ]; then
    log_error "Dieses Skript muss mit sudo ausgefuehrt werden!"
    exit 1
fi

# 2. Projektverzeichnis dynamisch erkennen
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$SCRIPT_DIR}"
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
PROJECT_USER="${PROJECT_USER:-pi}"
PROJECT_GROUP="${PROJECT_GROUP:-$PROJECT_USER}"
SERVICE_NAME="smartmeter"
NGINX_SITE_NAME="smartmeter"

log_info "Projektverzeichnis: $PROJECT_DIR"
log_info "Service-Name: $SERVICE_NAME"
log_info "Projektbenutzer: $PROJECT_USER"

require_file "$PROJECT_DIR/requirements.txt"
require_file "$PROJECT_DIR/app.py"
require_file "$PROJECT_DIR/db.py"
require_file "$PROJECT_DIR/cronjob_wrapper.sh"
require_file "$PROJECT_DIR/manual_import.sh"

if [ -f "$PROJECT_DIR/smartmeter.db" ]; then
    log_warn "Bestehende Datenbank gefunden und bleibt erhalten: $PROJECT_DIR/smartmeter.db"
else
    log_info "Noch keine Datenbank gefunden; sie wird bei Bedarf neu erstellt."
fi

# 3. System aktualisieren
log_info "Aktualisiere System..."
apt-get update
apt-get upgrade -y

# 4. Installiere erforderliche Pakete
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

# 5. Virtuelle Python-Umgebung
log_info "Pruefe virtuelle Python-Umgebung..."
if [ ! -d "$PROJECT_DIR/venv" ]; then
    python3 -m venv "$PROJECT_DIR/venv"
    log_info "Virtuelle Umgebung erstellt"
else
    log_warn "Virtuelle Umgebung existiert bereits"
fi

# 6. Aktiviere virtuelle Umgebung und installiere Dependencies
log_info "Installiere Python-Abhaengigkeiten..."
# shellcheck disable=SC1091
source "$PROJECT_DIR/venv/bin/activate"
pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt"

# 7. Initialisiere Datenbank, ohne bestehende Daten zu loeschen
log_info "Pruefe Datenbank..."
cd "$PROJECT_DIR"
python3 - << 'PYTHON_INIT'
from db import db_health_check

success, message = db_health_check()
print(f"Datenbank Status: {message}")
raise SystemExit(0 if success else 1)
PYTHON_INIT

# 8. Setze Dateiberechtigungen
log_info "Setze Dateiberechtigungen..."
if id "$PROJECT_USER" >/dev/null 2>&1; then
    if getent group "$PROJECT_GROUP" >/dev/null 2>&1; then
        chown -R "$PROJECT_USER:$PROJECT_GROUP" "$PROJECT_DIR"
    else
        chown -R "$PROJECT_USER" "$PROJECT_DIR"
    fi
else
    log_warn "Benutzer '$PROJECT_USER' existiert nicht; ueberspringe chown."
fi
chmod +x "$PROJECT_DIR/cronjob_wrapper.sh"
chmod +x "$PROJECT_DIR/manual_import.sh"
chmod +x "$PROJECT_DIR/app.py"

# 9. Systemd Service
log_info "Erstelle systemd Service..."
cat > "/etc/systemd/system/${SERVICE_NAME}.service" << SYSTEMD_SERVICE
[Unit]
Description=Smartmeter Flask Application
After=network.target

[Service]
Type=simple
User=${PROJECT_USER}
WorkingDirectory=${PROJECT_DIR}
ExecStart=${PROJECT_DIR}/venv/bin/python ${PROJECT_DIR}/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SYSTEMD_SERVICE

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
log_info "Systemd Service installiert: ${SERVICE_NAME}.service"

# 10. Cronjob einrichten
log_info "Richte Cronjob ein..."
CRON_JOB="* * * * * ${PROJECT_DIR}/cronjob_wrapper.sh"
if id "$PROJECT_USER" >/dev/null 2>&1; then
    EXISTING_CRON="$(mktemp)"
    crontab -u "$PROJECT_USER" -l 2>/dev/null | grep -v "cronjob_wrapper.sh" > "$EXISTING_CRON" || true
    {
        cat "$EXISTING_CRON"
        echo "$CRON_JOB"
    } | crontab -u "$PROJECT_USER" -
    rm -f "$EXISTING_CRON"
    log_info "Cronjob eingerichtet (jede Minute): $CRON_JOB"
else
    log_warn "Benutzer '$PROJECT_USER' existiert nicht; Cronjob wurde nicht eingerichtet."
fi

# 11. Nginx Konfigurieren (Reverse Proxy fuer Port 80)
log_info "Konfiguriere nginx als Reverse Proxy..."
rm -f /etc/nginx/sites-enabled/default

cat > "/etc/nginx/sites-available/${NGINX_SITE_NAME}" << NGINX_CONFIG
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    server_name muc localhost 127.0.0.1 _;
    root ${PROJECT_DIR};

    client_max_body_size 10M;

    access_log /var/log/nginx/smartmeter_access.log;
    error_log /var/log/nginx/smartmeter_error.log;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;

        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /static/ {
        alias ${PROJECT_DIR}/static/;
        expires 1h;
        add_header Cache-Control "public, immutable";
    }

    location /health {
        access_log off;
        return 200 "OK\\n";
        add_header Content-Type text/plain;
    }
}
NGINX_CONFIG

ln -sf "/etc/nginx/sites-available/${NGINX_SITE_NAME}" "/etc/nginx/sites-enabled/${NGINX_SITE_NAME}"

if nginx -t >/dev/null 2>&1; then
    log_info "Nginx Konfiguration OK"
    systemctl enable nginx
    systemctl restart nginx
    log_info "Nginx gestartet und aktiviert"
else
    log_error "Nginx Konfiguration fehlerhaft!"
    nginx -t
    exit 1
fi

# 12. Netzwerk-Bridge Setup (optional)
log_info ""
log_info "Netzwerk-Bridge Konfiguration"
log_info "================================"
echo ""
if [ "${SKIP_NETWORK_SETUP:-0}" = "1" ]; then
    log_info "Netzwerk-Bridge Setup im Update-Modus uebersprungen"
    log_info "Kann spaeter manuell ausgefuehrt werden: sudo bash $PROJECT_DIR/network_setup.sh"
else
    echo "Dieses Skript unterstuetzt automatisch:"
    echo "  - NetworkManager (moderne Raspberry Pi OS Bookworm)"
    echo "  - dhcpcd (aeltere Varianten)"
    echo ""
    read -p "Soll die Netzwerk-Bridge (WiFi <-> LAN zum MUC) konfiguriert werden? (j/n): " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Jj]$ ]]; then
        log_info "Starte Netzwerk-Bridge Setup (Auto-Detection aktiv)..."
        chmod +x "$PROJECT_DIR/network_setup.sh"
        bash "$PROJECT_DIR/network_setup.sh"

        echo ""
        log_warn "Reboot erforderlich fuer Netzwerk-Aenderungen!"
        echo ""
        read -p "Jetzt neustarten? (j/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Jj]$ ]]; then
            log_info "System wird neu gestartet..."
            sleep 2
            reboot
        else
            log_warn "Bitte spaeter manuell neustarten: sudo reboot"
        fi
    else
        log_info "Netzwerk-Bridge Setup uebersprungen"
        log_info "Kann spaeter manuell ausgefuehrt werden: sudo bash $PROJECT_DIR/network_setup.sh"
    fi
fi

# 13. Startmoeglichkeiten
echo ""
echo "================================================================"
echo -e "${GREEN}Setup abgeschlossen!${NC}"
echo "================================================================"
echo ""
echo "VERWENDUNG:"
echo ""
echo "  Web-Interface:"
echo "    http://muc         (Port 80 - ueber nginx)"
echo "    http://localhost   (lokal)"
echo ""
echo "  MUC Smartmeter (wenn Bridge konfiguriert):"
echo "    http://muc:8080    (Portweiterleitung extern)"
echo "    http://192.168.100.101 (direkt im LAN)"
echo ""
echo "  Service-Befehle:"
echo "    sudo systemctl start $SERVICE_NAME"
echo "    sudo systemctl stop $SERVICE_NAME"
echo "    sudo systemctl restart $SERVICE_NAME"
echo "    sudo systemctl enable $SERVICE_NAME"
echo "    sudo systemctl status $SERVICE_NAME"
echo ""
echo "  Logs anschauen:"
echo "    sudo journalctl -u $SERVICE_NAME -f"
echo "    sudo tail -f /var/log/nginx/smartmeter_access.log"
echo "    tail -f $PROJECT_DIR/smartmeter.log"
echo ""
echo "  Sensoren verwalten:"
echo "    Web-Browser: http://muc/sensors"
echo ""
echo "  Manueller Datenimport (einmalig, optional):"
echo "    $PROJECT_DIR/manual_import.sh"
echo ""
echo "  Netzwerk-Bridge nachtraeglich konfigurieren:"
echo "    sudo bash $PROJECT_DIR/network_setup.sh"
echo ""
echo "  Manueller Start (fuer Debugging):"
echo "    cd $PROJECT_DIR"
echo "    source venv/bin/activate"
echo "    python3 app.py"
echo ""
echo "================================================================"
echo -e "${GREEN}Smartmeter ist bereit!${NC}"
echo "================================================================"
