# VERA Office - Quick Start

## 🚀 Sandbox starten (1 Befehl)

```powershell
cd C:\Jarvix\vera-office
.\start-vera.ps1
```

## 🔧 In die Sandbox einsteigen

```powershell
docker exec -it vera-backend bash
```

**Verfügbare Tools in der Sandbox:**
- `pwsh` oder `ps1` → PowerShell Core
- `md <name>` → Ordner erstellen (mkdir alias)
- `cls` → Terminal leeren (clear alias)
- `ll` → Verzeichnis-Listing (ls -lah alias)
- `vim`, `nano` → Text-Editoren
- `curl`, `wget` → Downloads
- `git` → Version Control
- `htop` → Prozess-Monitor
- `jq` → JSON-Parser

## 📁 Wichtige Pfade in der Sandbox

```bash
/app/backend/       # Backend-Code
/app/data/          # Datenbank & Dokumente (persistent)
/app/config/        # Konfiguration
/app/logs/          # Logs
```

## 🧪 Backend API testen

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/documents
```

## 🛑 Sandbox stoppen

```powershell
cd C:\Jarvix\vera-office\docker
docker-compose down
```

---

**Tipp:** Alle Änderungen in `/app/data/` bleiben nach Container-Neustart erhalten (Volume-Mount).
