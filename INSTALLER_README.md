# VERA Office Installer - v2.0.0

## Was ist enthalten?

### Backend-Features
| Feature | Dateien | Beschreibung |
|---------|---------|--------------|
| **BLZK-Integration** | `modules/qm/blzk/*` | Bayerische Landeszahnärztekammer - Scraping, Credentials, Requirements |
| **USB-Import** | `api/usb_import.py` | Dokumente direkt vom USB-Stick importieren |
| **JWT Auto-Generation** | `config.py` | Automatische Secret-Generierung beim ersten Start |
| **User Rate-Limit** | `api/auth.py` | Schutz gegen Brute-Force bei User-Erstellung |
| **Dual-Platform Watchdog** | `core/systemd_watchdog.py`, `core/health.py` | Überwachung auf Linux (systemd) + Windows |
| **FTS5 Volltextsuche** | `db/database.py` | SQLite Full-Text-Search für Dokumente |
| **SQL Aggregation** | `modules/erp/calculator.py` | Performante Auswertungen direkt in SQL |

### Frontend-Features
| Feature | Dateien |
|---------|---------|
| **BLZK Einstellungen** | `views/qm/BLZKSettingsView.vue` |
| **BLZK Dokumente** | `views/qm/BLZKDocumentsView.vue` |
| **BLZK Document Card** | `components/QM/BLZKDocumentCard.vue` |
| **Requirements Link** | `components/QM/RequirementsLink.vue` |
| **QM API Service** | `services/qm-api.ts` (erweitert) |

### Service-Integration
- **Linux:** `vera-office.service` (systemd Unit) + `install-systemd.sh`
- **Windows:** `install_windows_service.ps1` (NSSM-basiert, Autostart)

### Dependencies (neu in v2.0.0)
- `beautifulsoup4` - BLZK Web-Scraping
- `httpx` - Async HTTP Client
- `cryptography` - JWT/SSL

---

## Installation

### Windows (Installer)
1. `VERA-Office-Setup-2.0.0.exe` ausführen
2. Installationsverzeichnis wählen (Default: `C:\VERA-Office`)
3. Optional: "Windows-Dienst installieren" anhaken → Autostart
4. Nach Installation: http://localhost:8080 öffnet sich automatisch

### Windows (manuell)
```powershell
cd C:\VERA-Office
.\start-vera.bat
```

### Linux (systemd)
```bash
# Dateien kopieren
sudo cp vera-office.service /etc/systemd/system/
sudo chmod +x install-systemd.sh
sudo ./install-systemd.sh

# Service starten
sudo systemctl enable vera-office
sudo systemctl start vera-office
```

---

## Build (für Entwickler)

```powershell
# Aus dem Projekt-Root:
.\BUILD_INSTALLER.ps1
```

**Voraussetzungen:**
- Inno Setup 6 (`C:\Program Files (x86)\Inno Setup 6\`)
- Node.js (für Frontend-Build)
- `installer/python-embed/` entpackt

**Output:** `D:\VERA-Office-Installer\VERA-Office-Setup-2.0.0.exe`

---

## Troubleshooting

| Problem | Lösung |
|---------|--------|
| Port 8080 belegt | `.env` → `VERA_PORT=8081` |
| NSSM nicht gefunden | `winget install nssm` |
| OCR funktioniert nicht | Tesseract-Pfad in `.env` prüfen |
| BLZK-Login schlägt fehl | Credentials in VERA UI unter QM → BLZK Einstellungen |
