#!/bin/bash
################################################################################
# update.sh - Sicheres Update fuer bestehende Smartmeter/MUC-Pi Installationen
#
# Standard:
#   bash update.sh
#
# Falls auf einem Pi noch lokale Code-Aenderungen aus alten manuellen Fixes
# existieren:
#   bash update.sh --discard-local-code
#
# Lokale Daten wie smartmeter.db, logs/ und venv/ werden nicht geloescht.
################################################################################

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
BACKUP_DIR="$PROJECT_DIR/backups"
SERVICE_NAME="${SERVICE_NAME:-smartmeter}"
DISCARD_LOCAL_CODE=false

if [ "${1:-}" = "--discard-local-code" ]; then
    DISCARD_LOCAL_CODE=true
elif [ "${1:-}" != "" ]; then
    log_error "Unbekannte Option: $1"
    echo "Verwendung: bash update.sh [--discard-local-code]"
    exit 1
fi

cd "$PROJECT_DIR"

if [ ! -d ".git" ]; then
    log_error "Dieses Verzeichnis ist kein Git-Repository: $PROJECT_DIR"
    exit 1
fi

mkdir -p "$BACKUP_DIR"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"

log_info "Projektverzeichnis: $PROJECT_DIR"

if [ -f "smartmeter.db" ]; then
    DB_BACKUP="$BACKUP_DIR/smartmeter-$TIMESTAMP.db"
    cp -p "smartmeter.db" "$DB_BACKUP"
    log_info "Datenbank gesichert: $DB_BACKUP"
else
    log_warn "Keine smartmeter.db gefunden; ueberspringe DB-Backup."
fi

CURRENT_BRANCH="$(git branch --show-current)"
if [ -z "$CURRENT_BRANCH" ]; then
    log_error "Kein aktiver Git-Branch gefunden."
    exit 1
fi

UPSTREAM="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
if [ -z "$UPSTREAM" ]; then
    UPSTREAM="origin/$CURRENT_BRANCH"
    log_warn "Kein Upstream gesetzt; verwende $UPSTREAM."
fi

log_info "Hole aktuellen Stand von GitHub..."
git fetch --prune

LOCAL_STATUS="$(git status --porcelain --untracked-files=no)"
if [ -n "$LOCAL_STATUS" ]; then
    PATCH_FILE="$BACKUP_DIR/local-code-changes-$TIMESTAMP.patch"
    git diff > "$PATCH_FILE"
    git diff --cached >> "$PATCH_FILE"

    if [ "$DISCARD_LOCAL_CODE" = true ]; then
        log_warn "Lokale Code-Aenderungen gefunden und als Patch gesichert: $PATCH_FILE"
        log_warn "Setze lokalen Code auf $UPSTREAM zurueck. Lokale Daten bleiben erhalten."
        git reset --hard "$UPSTREAM"
    else
        log_error "Lokale Code-Aenderungen gefunden. Update wurde gestoppt."
        echo ""
        echo "Gesicherter Patch:"
        echo "  $PATCH_FILE"
        echo ""
        echo "Wenn diese Aenderungen nur alte manuelle Pfad-Fixes waren, fuehre aus:"
        echo "  bash update.sh --discard-local-code"
        echo ""
        echo "Deine Datenbank wurde bereits gesichert. smartmeter.db wird nicht geloescht."
        exit 1
    fi
else
    log_info "Keine lokalen Code-Aenderungen gefunden."
    log_info "Spiele Update ein..."
    git pull --ff-only
fi

log_info "Pruefe setup.sh Syntax..."
bash -n setup.sh

log_info "Fuehre setup.sh im Update-Modus aus..."
sudo env SKIP_NETWORK_SETUP=1 bash setup.sh

log_info "Starte Service neu..."
sudo systemctl restart "$SERVICE_NAME"

log_info "Update abgeschlossen."
echo ""
echo "Pruefen:"
echo "  sudo systemctl status $SERVICE_NAME"
echo "  sudo journalctl -u $SERVICE_NAME -n 50"
