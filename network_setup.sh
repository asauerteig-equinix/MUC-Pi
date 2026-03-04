#!/bin/bash
################################################################################
# network_setup.sh - Netzwerk-Bridge Konfiguration für Raspberry Pi
#
# Konfiguriert:
# - WiFi-Verbindung: Zum Hauptnetzwerk (DHCP oder statisch)
# - Ethernet/LAN: Bridge zum MUC Smartmeter
# - Hostname: "muc" im lokalen Netzwerk
# - Port Forwarding: 8080 → MUC
#
# Verwendung: sudo bash network_setup.sh
################################################################################

set -e

echo "================================================================"
echo "Netzwerk-Bridge Konfiguration für Smartmeter"
echo "================================================================"
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check root
if [ "$EUID" -ne 0 ]; then
    log_error "Dieses Skript benötigt sudo!"
    exit 1
fi

# Schritt 1: Systemd-resolved konfigurieren
log_info "Konfiguriere DNS (systemd-resolved)..."
mkdir -p /etc/systemd/resolved.conf.d
cat > /etc/systemd/resolved.conf.d/muc.conf << 'EOF'
[Resolve]
DNS=8.8.8.8 8.8.4.4
FallbackDNS=1.1.1.1 1.0.0.1
DNS=127.0.0.1
DNSSEC=no
EOF
systemctl restart systemd-resolved
log_info "DNS konfiguriert"

# Schritt 2: Hostname setzen
log_info "Setze Hostname auf 'muc'..."
hostnamectl set-hostname muc
sed -i 's/127.0.1.1.*/127.0.1.1       muc/g' /etc/hosts
echo "127.0.1.1       muc" >> /etc/hosts
log_info "Hostname gesetzt: $(hostname)"

# Schritt 3: Netzwerk-Interfaces prüfen
log_info "Prüfe Netzwerk-Interfaces..."
WIFI_IF=""
ETH_IF=""
AVAILABLE_IFS=$(ip link | grep ': ' | grep -v 'lo:' | awk -F': ' '{print $2}' | xargs)

echo "Verfügbare Interfaces: $AVAILABLE_IFS"
echo ""

# WiFi Interface (wlan0 oder wlan1)
for IF in wlan0 wlan1 wlp3s0 wlp4s0; do
    if ip link show "$IF" >/dev/null 2>&1; then
        WIFI_IF="$IF"
        log_info "WiFi Interface gefunden: $WIFI_IF"
        break
    fi
done

# Ethernet Interface (eth0 oder enp0s3)
for IF in eth0 enp0s3 enp2s0 enp0s31f6; do
    if ip link show "$IF" >/dev/null 2>&1; then
        ETH_IF="$IF"
        log_info "Ethernet Interface gefunden: $ETH_IF"
        break
    fi
done

if [ -z "$WIFI_IF" ] || [ -z "$ETH_IF" ]; then
    log_error "Nicht beide Interfaces gefunden!"
    log_info "WiFi: $WIFI_IF, Ethernet: $ETH_IF"
    exit 1
fi

echo ""

# Schritt 4: dhcpcd konfigurieren (für Static IP auf Ethernet)
log_info "Konfiguriere dhcpcd für statische Ethernet-IP..."
cat >> /etc/dhcpcd.conf << EOF

# Smartmeter Bridge
interface $ETH_IF
static ip_address=192.168.100.1/24
static routers=192.168.100.254
static domain_name_servers=8.8.8.8 8.8.4.4

# WiFi - DHCP
interface $WIFI_IF
EOF
log_info "dhcpcd konfiguriert"

# Schritt 5: iptables-persistent installieren
log_info "Installiere iptables-persistent..."
DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent

# Schritt 6: IP Forwarding aktivieren
log_info "Aktiviere IP Forwarding..."
echo "net.ipv4.ip_forward=1" | tee -a /etc/sysctl.conf
sysctl -p >/dev/null

# Schritt 7: iptables Rules
log_info "Konfiguriere iptables Regeln..."

# Alte Regeln löschen (falls vorhanden)
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X

# Forwarding zwischen den Interfaces
iptables -A FORWARD -i $WIFI_IF -o $ETH_IF -j ACCEPT
iptables -A FORWARD -i $ETH_IF -o $WIFI_IF -j ACCEPT

# NAT (Masquerading)
iptables -t nat -A POSTROUTING -o $WIFI_IF -j MASQUERADE

# Port Forwarding: 8080 → MUC:502 (MUC läuft auf Port 502)
# Externe Anfragen auf Port 8080 werden zum MUC weitergeleitet
iptables -t nat -A PREROUTING -p tcp --dport 8080 -j DNAT --to-destination 192.168.100.101:502
iptables -t nat -A POSTROUTING -p tcp --dport 502 -d 192.168.100.101 -j SNAT --to-source 192.168.100.1
iptables -A FORWARD -p tcp --dport 502 -d 192.168.100.101 -j ACCEPT

# Speichere iptables Regeln
iptables-save > /etc/iptables/rules.v4
log_info "iptables Regeln gespeichert"

# Schritt 8: Broadcasting auf Ethernet aktivieren
log_info "Aktiviere Broadcasting..."
echo "net.ipv4.icmp_echo_ignore_broadcasts=0" | tee -a /etc/sysctl.conf
sysctl -p >/dev/null

echo ""
echo "================================================================"
log_info "Netzwerk-Bridge Konfiguration abgeschlossen!"
echo "================================================================"
echo ""
echo "Konfiguration:"
echo "  WiFi Interface:     $WIFI_IF (DHCP vom Router)"
echo "  Ethernet Interface: $ETH_IF (Statisch 192.168.100.1/24)"
echo "  Hostname:           muc"
echo "  IP Forwarding:      Aktiviert"
echo "  Port Forwarding:    8080 → MUC:502"
echo ""
echo "Accesso:"
echo "  Smartmeter Dashboard:  http://muc"
echo "  MUC Smartmeter:        http://muc:8080"
echo ""
echo "Nächste Schritte:"
echo "  1. Ethernet-Kabel zum MUC verbinden"
echo "  2. Reboot durchführen: sudo reboot"
echo "  3. Nach dem Reboot prüfen:"
echo "     - ping muc"
echo "     - ping 192.168.100.101"
echo "     - curl http://muc"
echo ""
