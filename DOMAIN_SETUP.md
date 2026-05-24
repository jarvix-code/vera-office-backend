# VERA Office - Domain Setup (vera-office.local)

## Übersicht

**Ziel:** User tippt `vera-office.local` → landet automatisch auf HTTPS (Port 8443)

### Architektur

```
User Browser
    ↓
vera-office.local (mDNS Discovery)
    ↓
Port 80 (HTTP) → Redirect → Port 8443 (HTTPS)
    ↓
Caddy Reverse Proxy (Port 8443)
    ↓
VERA Backend (Port 8080)
```

## Komponenten

### 1. mDNS Service (Zeroconf)
- **Code:** `backend/core/mdns.py`
- **Registriert:** `vera-office.local` auf Port 8443
- **Protokoll:** `_https._tcp.local.`
- **Start:** Automatisch beim Backend-Start (Lifespan)

### 2. Caddy Reverse Proxy
- **Config:** `Caddyfile`
- **HTTPS Port:** 8443 (TLS internal certificate)
- **HTTP Port:** 80 (redirect to 8443)
- **Upstream:** localhost:8080 (VERA Backend)

### 3. VERA Backend
- **Port:** 8080 (HTTP, local only)
- **Nicht direkt erreichbar** von außen
- **Nur via Caddy Proxy**

## Setup

### 1. Caddy installieren
```powershell
# Windows (Chocolatey)
choco install caddy

# Oder manuell: https://caddyserver.com/download
```

### 2. Caddy starten
```powershell
cd C:\Jarvix\vera-office
caddy run --config Caddyfile
```

### 3. VERA Backend starten
```powershell
cd C:\Jarvix\vera-office
.\backend\venv\Scripts\activate
python -m backend.main
```

### 4. Testen
```powershell
# mDNS Check (funktioniert vera-office.local?)
ping vera-office.local

# HTTP Redirect Test
curl -I http://vera-office.local

# HTTPS Test (muss Zertifikatsfehler zeigen - internal cert)
curl -k https://vera-office.local:8443
```

## Windows Service (Production)

### Caddy als Service installieren
```powershell
# Admin PowerShell
cd C:\Jarvix\vera-office
caddy install --config Caddyfile

# Service starten
net start caddy
```

### VERA Backend als Service
```powershell
# TODO: NSSM (Non-Sucking Service Manager) nutzen
nssm install VERAOffice "C:\Jarvix\vera-office\backend\venv\Scripts\python.exe" "-m backend.main"
nssm set VERAOffice AppDirectory "C:\Jarvix\vera-office"
nssm start VERAOffice
```

## Troubleshooting

### mDNS funktioniert nicht
- **Problem:** `vera-office.local` kann nicht aufgelöst werden
- **Check:** Bonjour Service installiert? (iTunes/Apple Software)
  ```powershell
  Get-Service -Name "Bonjour*"
  ```
- **Fix:** Bonjour Service installieren (kommt mit iTunes)

### Port 80 ist bereits belegt
- **Problem:** Anderer Webserver läuft auf Port 80
- **Check:** 
  ```powershell
  netstat -ano | findstr :80
  ```
- **Fix 1:** Anderen Webserver stoppen
- **Fix 2:** Caddy auf anderen Port (z.B. 8000) und Port explizit nutzen: `vera-office.local:8000`

### HTTPS Zertifikat-Warnung
- **Normal!** Caddy nutzt self-signed internal certificate
- **Für Produktion:** Echtes Zertifikat via Let's Encrypt (nur mit öffentlicher Domain)
- **Für LAN:** User muss Warnung akzeptieren (einmalig)

## Port-Übersicht

| Port | Service | Protokoll | Zweck |
|------|---------|-----------|-------|
| 80 | Caddy | HTTP | Redirect → 8443 |
| 8443 | Caddy | HTTPS | Reverse Proxy → 8080 |
| 8080 | VERA Backend | HTTP | FastAPI App (local only) |
| 2019 | Caddy Admin | HTTP | Admin API (localhost) |

## Logs

### Caddy Logs
```powershell
# Access Log
Get-Content C:\Jarvix\vera-office\logs\caddy-access.log -Tail 50 -Wait

# Error Log (stdout)
journalctl -u caddy -f  # Linux
Get-WinEvent -LogName Application | Where-Object { $_.Source -eq "Caddy" }  # Windows
```

### VERA Backend Logs
```powershell
# Loguru stdout output (beim Start sichtbar)
python -m backend.main
```

## Nächste Schritte

- [ ] Installer: Caddy + VERA als Service installieren
- [ ] Bonjour-Check beim Setup (falls fehlt → Download-Link anzeigen)
- [ ] Zertifikat-Handling: User-Anleitung für Self-Signed Cert akzeptieren
- [ ] Auto-Update für Caddy-Config bei Portänderungen
