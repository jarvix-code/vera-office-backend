# VERA Office - USB + Domain Fix (2026-03-26)

## ✅ Task 1: USB-Folder-Auswahl UI

### Was wurde gemacht:
- **Frontend erweitert** (`frontend/src/views/CaptureView.vue`)
  - USB-Import zeigt jetzt Folder-Struktur (Tree-View)
  - User kann Ordner per Checkbox auswählen
  - Nur ausgewählte Ordner werden importiert
  - Zeigt file_count + size_mb pro Ordner
  - "Alle auswählen" / "Keine" Buttons
  - Live-Progress während Import

### API:
- Backend-API `/api/import-usb/scan` gibt bereits `folders[]` zurück ✓
- Neuer Endpoint: POST `/api/import-usb` mit `{ folders: ["path1", "path2"] }`
- Polling-Endpoint: GET `/api/import-usb/progress/{job_id}`

### User Flow:
1. User klickt "USB-Stick" auf Capture-Page
2. VERA scannt USB und zeigt Folder-Struktur
3. User wählt Ordner aus (oder "Alle auswählen")
4. User klickt "X Dateien importieren"
5. Import läuft im Hintergrund, Progress wird angezeigt
6. Nach Abschluss: Redirect zu /documents

### Dateien geändert:
- `frontend/src/views/CaptureView.vue` (UI + Logic)
- `backend/main.py` (USB-Import Router registriert)

---

## ✅ Task 2: Domain-Setup vera-office.local

### Ziel:
User tippt `vera-office.local` → landet automatisch auf HTTPS (Port 8443)

### Was wurde gemacht:

#### 1. mDNS aktiviert
- **Datei:** `backend/main.py`
- **Änderung:** mDNS Service-Registrierung wieder aktiviert
- **Port:** 8443 (HTTPS, nicht 8080!)
- **Service-Name:** `vera-office.local`
- **Protokoll:** `_https._tcp.local.`

#### 2. Caddy konfiguriert
- **Datei:** `Caddyfile`
- **HTTPS Port:** 8443 (TLS internal certificate)
- **HTTP Port:** 80 (Redirect zu 8443)
- **Upstream:** localhost:8080 (VERA Backend)
- **Fallback:** Wenn kein Port angegeben → Redirect zu 8443

#### 3. Architektur:
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

### Dateien geändert:
- `backend/main.py` (mDNS aktiviert)
- `Caddyfile` (HTTPS + Redirect konfiguriert)

### Neue Dateien:
- `DOMAIN_SETUP.md` (Dokumentation)
- `test_domain_setup.ps1` (Test-Script)

---

## Testing

### Frontend (USB-Folder-Auswahl):
```bash
cd C:\Jarvix\vera-office\frontend
npm run dev
# Öffne http://localhost:5173 → Capture → USB-Stick
```

### Backend (Domain-Setup):
```powershell
# Terminal 1: Caddy starten
cd C:\Jarvix\vera-office
caddy run --config Caddyfile

# Terminal 2: VERA Backend starten
cd C:\Jarvix\vera-office
.\backend\venv\Scripts\activate
python -m backend.main

# Terminal 3: Tests ausführen
.\test_domain_setup.ps1
```

### Browser-Test:
1. Öffne Browser
2. Tippe: `vera-office.local`
3. Erwartung: Redirect zu `https://vera-office.local:8443`
4. Zertifikat-Warnung akzeptieren (self-signed)
5. VERA Office Interface sollte laden

---

## Wichtige Hinweise

### mDNS / Bonjour:
- Windows benötigt **Bonjour Service** (kommt mit iTunes)
- Ohne Bonjour: `vera-office.local` funktioniert nicht
- Check: `Get-Service -Name "Bonjour*"`

### Port 80:
- **Benötigt Admin-Rechte** unter Windows
- Falls bereits belegt: Caddy auf anderen Port (z.B. 8000)
- Dann explizit Port angeben: `vera-office.local:8000`

### HTTPS Zertifikat:
- Caddy nutzt self-signed certificate (intern)
- Browser zeigt Warnung → User muss akzeptieren
- Für echtes Zertifikat: Let's Encrypt (nur mit öffentlicher Domain)

---

## Nächste Schritte (TODO)

- [ ] Installer: Caddy + VERA als Windows Service
- [ ] Bonjour-Check beim Setup (falls fehlt → Download-Link)
- [ ] User-Anleitung: HTTPS-Warnung akzeptieren
- [ ] Auto-Update Caddy-Config bei Portänderungen
- [ ] USB-Import: Error-Handling verbessern
- [ ] USB-Import: Preview für Dateien vor Import
