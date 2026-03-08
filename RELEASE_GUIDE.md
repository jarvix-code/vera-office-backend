# VERA Office - Release & Update Guide

## 🚀 Releases erstellen (GitHub)

**Entwicklermodus:** VERA nutzt GitHub Releases als Update-Quelle

### 1. Vorbereitung

**Version in Config aktualisieren:**
```yaml
# config/vera.yaml
app_version: "1.0.1"  # Neue Version
```

**Changelog erstellen:**
```markdown
# CHANGELOG.md
## v1.0.1 - 2026-03-08

### Fixed
- Bug #7: Sidebar Navigation funktioniert jetzt
- Bug #11: Chat Authentication gefixt
- Qwen Prompt-Format für Deutsch optimiert

### Added
- GitHub Release Update-System
- Telegram Bot Bug-Reporting

### Changed
- Multi-LLM: Qwen 2.5-1.5B für schnelle Chat-Antworten
```

### 2. Release-ZIP erstellen

**PowerShell:**
```powershell
# In VERA Root-Verzeichnis
$version = "1.0.1"
$releaseDir = "release"
$zipFile = "vera-office-$version.zip"

# Erstelle Release-Ordner
New-Item -ItemType Directory -Force -Path $releaseDir

# Kopiere wichtige Dateien (ohne data/, logs/, etc)
Copy-Item -Path "backend" -Destination "$releaseDir\backend" -Recurse -Exclude "__pycache__","*.pyc"
Copy-Item -Path "frontend" -Destination "$releaseDir\frontend" -Recurse -Exclude "node_modules"
Copy-Item -Path "config" -Destination "$releaseDir\config" -Recurse
Copy-Item -Path "README.md" -Destination "$releaseDir\"
Copy-Item -Path "requirements.txt" -Destination "$releaseDir\"

# Erstelle ZIP
Compress-Archive -Path "$releaseDir\*" -DestinationPath $zipFile -Force

# Cleanup
Remove-Item -Path $releaseDir -Recurse -Force

Write-Host "✅ Release ZIP erstellt: $zipFile"
```

### 3. GitHub Release erstellen

**Option A: GitHub Web UI**
1. Gehe zu: https://github.com/boris-reimers/vera-office/releases/new
2. Tag: `v1.0.1` (mit "v" prefix!)
3. Release Title: `VERA Office v1.0.1`
4. Beschreibung: Kopiere Changelog-Eintrag
5. Upload: `vera-office-1.0.1.zip`
6. Publish Release

**Option B: GitHub CLI (gh)**
```bash
# Install: https://cli.github.com/
gh release create v1.0.1 \
  vera-office-1.0.1.zip \
  --title "VERA Office v1.0.1" \
  --notes-file CHANGELOG.md
```

---

## 📥 Updates installieren (VERA Client)

### Via Web-UI

**1. Update-Status prüfen:**
```
GET http://localhost:8000/api/system/update-status
```

**Response:**
```json
{
  "current_version": "1.0.0-alpha",
  "update_available": false,
  "latest_version": null,
  "last_check": "2026-03-08T15:30:00"
}
```

**2. Nach Updates suchen:**
```
POST http://localhost:8000/api/system/check-update
```

**Response (wenn Update verfügbar):**
```json
{
  "update_available": true,
  "version": "1.0.1",
  "changelog": "### Fixed\n- Bug #7: Sidebar...",
  "download_url": "https://github.com/.../releases/download/v1.0.1/vera-office-1.0.1.zip"
}
```

**3. Update installieren:**
```
POST http://localhost:8000/api/system/apply-update
Body: {"version": "1.0.1"}
```

**Response:**
```json
{
  "success": true,
  "message": "✅ Update auf Version 1.0.1 erfolgreich installiert.\n⚠️ Neustart erforderlich!",
  "version": "1.0.1"
}
```

**4. VERA neu starten:**
```powershell
# Backend neu starten
taskkill /F /IM python.exe
cd C:\Jarvix\vera-office
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Via PowerShell (direkt)

```powershell
# 1. Update-Check
$token = "<JWT_TOKEN>"  # Via /api/auth/login
$headers = @{"Authorization" = "Bearer $token"}

$check = Invoke-RestMethod -Uri "http://localhost:8000/api/system/check-update" -Method Post -Headers $headers

if ($check.update_available) {
    Write-Host "✨ Update verfügbar: $($check.version)"
    
    # 2. Update installieren
    $body = @{version = $check.version} | ConvertTo-Json
    $result = Invoke-RestMethod -Uri "http://localhost:8000/api/system/apply-update" -Method Post -Headers $headers -Body $body -ContentType "application/json"
    
    Write-Host $result.message
    
    if ($result.success) {
        Write-Host "⚠️ VERA Backend muss neu gestartet werden!"
    }
} else {
    Write-Host "✅ VERA ist aktuell ($($check.version))"
}
```

---

## 🔧 Troubleshooting

### Update-Check funktioniert nicht
```powershell
# Prüfe GitHub Erreichbarkeit
Invoke-RestMethod -Uri "https://api.github.com/repos/boris-reimers/vera-office/releases/latest"
```

### Release nicht gefunden (404)
- Prüfe ob Release PUBLIC ist (nicht Draft)
- Prüfe ob Repo-Name in `vera.yaml` stimmt
- Prüfe ob Tag mit "v" beginnt (z.B. `v1.0.1`)

### ZIP-Download schlägt fehl
- Prüfe ob ZIP-Asset im Release vorhanden
- Prüfe Dateigröße (GitHub Limit: 2 GB)

---

## 📋 Checkliste für Releases

- [ ] Version in `config/vera.yaml` aktualisiert
- [ ] Changelog in `CHANGELOG.md` dokumentiert
- [ ] Release-ZIP erstellt (ohne data/, logs/, __pycache__)
- [ ] Git Commit + Push
- [ ] GitHub Release erstellt (Tag: `vX.Y.Z`)
- [ ] ZIP als Asset hochgeladen
- [ ] Release als PUBLIC markiert
- [ ] Update-Test durchgeführt
- [ ] Rollback getestet (Backup funktioniert)

---

## 🔄 Rollback (bei Problemen)

**VERA erstellt automatisch Backup vor jedem Update:**

```powershell
# Finde letzte Backups
ls C:\Jarvix\vera-office\data\backups\pre-update\ | Sort-Object LastWriteTime -Descending

# Restore Backup
$backup = "backup_1.0.0-alpha_20260308_153000"
Copy-Item -Path "C:\Jarvix\vera-office\data\backups\pre-update\$backup\*" -Destination "C:\Jarvix\vera-office\" -Recurse -Force

# Backend neu starten
```

---

**Entwickelt mit ❤️ von Boris Reimers**
