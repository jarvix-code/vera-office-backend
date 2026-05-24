# VERA Office - Deployment Checklist (USB + Domain Fix)

## Vor dem Deployment

### 1. Dependencies prüfen
```powershell
# Bonjour Service (für mDNS)
Get-Service -Name "Bonjour*"
# Falls nicht vorhanden: iTunes installieren

# Caddy installiert?
caddy version
# Falls nicht vorhanden: choco install caddy
```

### 2. Code-Review
- [ ] `frontend/src/views/CaptureView.vue` - USB-Folder-Selection UI
- [ ] `backend/api/usb_import.py` - API Endpoints
- [ ] `backend/main.py` - Router registriert, mDNS aktiviert
- [ ] `Caddyfile` - HTTPS + Redirect konfiguriert

### 3. Ports freigeben
```powershell
# Check Port 80 (HTTP)
netstat -ano | findstr :80

# Check Port 8443 (HTTPS)
netstat -ano | findstr :8443

# Check Port 8080 (Backend)
netstat -ano | findstr :8080
```

## Deployment Steps

### 1. Backend starten
```powershell
cd C:\Jarvix\vera-office
.\backend\venv\Scripts\activate
python -m backend.main
```

**Erwartete Logs:**
```
[OK] mDNS Service registriert: vera-office.local:8443
VERA Office Backend bereit auf 0.0.0.0:8080
```

### 2. Caddy starten
```powershell
cd C:\Jarvix\vera-office
caddy run --config Caddyfile
```

**Erwartete Logs:**
```
https://vera-office.local:8443
http://vera-office.local:80
```

### 3. Tests ausführen
```powershell
# Automated Test Suite
.\test_domain_setup.ps1

# Manual Browser Test
# Öffne Browser, gehe zu: vera-office.local
```

## Test Cases

### USB-Folder-Selection
- [ ] USB-Stick einstecken
- [ ] VERA öffnen → Capture → USB-Stick
- [ ] Folder-Struktur wird angezeigt
- [ ] file_count + size_mb pro Ordner sichtbar
- [ ] Checkboxes funktionieren
- [ ] "Alle auswählen" / "Keine" Buttons funktionieren
- [ ] Import startet mit ausgewählten Ordnern
- [ ] Progress wird angezeigt
- [ ] Nach Abschluss: Redirect zu /documents

### Domain vera-office.local
- [ ] Browser: `vera-office.local` → Redirect zu `https://vera-office.local:8443`
- [ ] Browser: `http://vera-office.local` → Redirect zu HTTPS
- [ ] Browser: `http://vera-office.local:80` → Redirect zu HTTPS
- [ ] Browser: `https://vera-office.local:8443` → VERA Interface lädt
- [ ] iPad/iPhone: `vera-office.local` funktioniert (mDNS)

### mDNS Discovery
- [ ] Windows: `ping vera-office.local` funktioniert
- [ ] iPad: Safari kann `vera-office.local` auflösen
- [ ] Android: Chrome kann `vera-office.local` auflösen (mit Bonjour App)

## Troubleshooting

### mDNS funktioniert nicht
**Problem:** `vera-office.local` kann nicht aufgelöst werden

**Check:**
```powershell
Get-Service -Name "Bonjour*"
```

**Fix:**
- iTunes installieren (enthält Bonjour Service)
- Oder: Bonjour Print Services manuell installieren
- Service neustarten: `Restart-Service -Name "Bonjour Service"`

### Port 80 bereits belegt
**Problem:** Caddy kann nicht auf Port 80 binden

**Check:**
```powershell
netstat -ano | findstr :80
```

**Fix Option 1:** Anderen Webserver stoppen
```powershell
# IIS stoppen
iisreset /stop

# Apache stoppen
net stop Apache2.4
```

**Fix Option 2:** Caddy auf anderen Port
```
# Caddyfile ändern:
http_port 8000

# Browser: vera-office.local:8000
```

### HTTPS Zertifikat-Warnung
**Problem:** Browser zeigt "Unsichere Verbindung"

**Ursache:** Self-signed certificate (normal!)

**User-Anleitung:**
1. Warnung lesen
2. "Erweitert" / "Advanced" klicken
3. "Trotzdem fortfahren" / "Proceed anyway"
4. VERA lädt

**Alternative:** Zertifikat importieren (für IT-Admin)
```powershell
# Caddy internal cert exportieren
caddy trust
```

### Backend startet nicht
**Problem:** Port 8080 bereits belegt

**Check:**
```powershell
netstat -ano | findstr :8080
```

**Fix:**
- Andere VERA-Instanz stoppen
- Oder: Port in `backend/config.py` ändern (dann auch Caddyfile anpassen!)

## Production Deployment (Windows Service)

### Caddy als Service
```powershell
# Admin PowerShell
cd C:\Jarvix\vera-office
caddy stop  # Falls bereits läuft
caddy install --config Caddyfile

# Service starten
net start caddy

# Auto-start aktivieren
sc config caddy start= auto
```

### VERA Backend als Service (NSSM)
```powershell
# NSSM installieren
choco install nssm

# Service erstellen
nssm install VERAOffice "C:\Jarvix\vera-office\backend\venv\Scripts\python.exe"
nssm set VERAOffice AppParameters "-m backend.main"
nssm set VERAOffice AppDirectory "C:\Jarvix\vera-office"
nssm set VERAOffice DisplayName "VERA Office Backend"
nssm set VERAOffice Description "VERA Office Document Agent"
nssm set VERAOffice Start SERVICE_AUTO_START

# Service starten
nssm start VERAOffice

# Status prüfen
nssm status VERAOffice
```

## Rollback Plan

Falls etwas schief geht:

### Code zurücksetzen
```powershell
cd C:\Jarvix\vera-office
git stash  # Änderungen temporär speichern
git checkout HEAD~1  # Vorherige Version
```

### Services stoppen
```powershell
# Caddy
net stop caddy

# VERA Backend
nssm stop VERAOffice

# Oder manuell
Get-Process -Name "python" | Where-Object { $_.Path -like "*vera-office*" } | Stop-Process
```

## Success Criteria

Deployment ist erfolgreich wenn:
- ✅ User tippt `vera-office.local` → VERA lädt
- ✅ HTTP wird automatisch zu HTTPS redirected
- ✅ USB-Import zeigt Folder-Struktur
- ✅ Nur ausgewählte Ordner werden importiert
- ✅ iPad/iPhone kann vera-office.local erreichen
- ✅ Keine Fehler in Backend/Caddy Logs

## Nächste Iteration (TODO)

- [ ] Installer-Script für One-Click-Setup
- [ ] Auto-Detection: Bonjour fehlt → Download-Link
- [ ] User-Onboarding: HTTPS-Warnung erklären
- [ ] USB-Import: Preview vor Import
- [ ] USB-Import: Duplikat-Check VOR Import
- [ ] Domain-Setup: Fallback auf IP wenn mDNS fehlt
