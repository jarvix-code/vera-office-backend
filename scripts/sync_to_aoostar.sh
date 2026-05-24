#!/usr/bin/env bash
# sync_to_aoostar.sh — VERA Office Sync: Dev -> Aoostar (192.168.178.65)
# Atlas Infra (vera_facility_manager) — 2026-05-24
#
# Strategie: git pull auf Aoostar via SSH (primaer), Fallback rsync
# Aoostar: vera@192.168.178.65, VERA laeuft unter /opt/vera-office/

set -euo pipefail

AOOSTAR_HOST="192.168.178.65"
AOOSTAR_USER="vera"
AOOSTAR_PATH="/opt/vera-office"
LOG_FILE="/opt/vera-office/logs/sync_aoostar.log"
BRANCH="master"

log() {
    echo "[2026-05-24 16:16:27] " | tee -a ""
}

mkdir -p "."

log "=== VERA Sync Dev->Aoostar gestartet ==="

# 1. SSH-Erreichbarkeit pruefen
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "@" "echo OK" > /dev/null 2>&1; then
    log "FEHLER: Aoostar  nicht erreichbar via SSH."
    log "Fallback: rsync wird versucht..."

    rsync -avz --progress         --exclude='.git/'         --exclude='backend/cache/'         --exclude='data/*.db'         --exclude='logs/'         --exclude='*.pyc'         --exclude='__pycache__/'         --exclude='.venv/'         --exclude='python/'         --exclude='installer/'         --exclude='certs/'         --exclude='keys/'         /opt/vera-office/         "@:/"         2>&1 | tee -a "" || {
            log "KRITISCH: rsync ebenfalls fehlgeschlagen. Manuelle Intervention noetig."
            exit 1
        }
    log "Fallback rsync erfolgreich."
    exit 0
fi

# 2. Primaer: git pull auf Aoostar
log "SSH OK — fuehre git pull auf Aoostar aus..."

ssh "@" "
    set -e
    cd 
    echo '--- git status ---'
    git status --short
    echo '--- git pull ---'
    git pull origin 
    echo '--- Health Check ---'
    if systemctl is-active --quiet vera.service 2>/dev/null; then
        echo 'Restarting vera.service...'
        sudo systemctl restart vera.service
        sleep 3
        systemctl is-active vera.service && echo 'Service: OK' || echo 'Service: FAILED'
    else
        echo 'vera.service nicht aktiv — kein Restart.'
    fi
" 2>&1 | tee -a ""

log "=== Sync abgeschlossen ==="
exit 0
