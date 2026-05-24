# VERA Sandbox - Cheatsheet

## 🚪 Rein/Raus

```bash
# Reingehen
docker exec -it vera-backend bash

# PowerShell starten (in der Sandbox)
pwsh

# Rausgehen
exit    # (oder Ctrl+D)
```

## 🛠️ Wichtigste Befehle

### Dateisystem
```bash
md test             # Ordner erstellen (mkdir -p)
ll                  # Verzeichnis anzeigen (ls -lah)
cd /app/backend     # Backend-Code
cd /app/data        # Datenbank & Dokumente
tree /app           # Struktur anzeigen
```

### Prozesse & System
```bash
htop                # Prozess-Monitor (q zum Beenden)
ps aux              # Prozess-Liste
df -h               # Speicherplatz
du -sh *            # Ordnergröße
```

### API & Netzwerk
```bash
curl http://localhost:8000/health              # Health Check
curl http://localhost:8000/api/v1/documents    # Dokumente abrufen
curl -X POST http://localhost:8000/api/v1/upload -F "file=@test.pdf"  # Upload

# JSON pretty-print
curl http://localhost:8000/api/v1/documents | jq .
```

### Logs & Debugging
```bash
# Backend-Logs (live)
tail -f /app/logs/vera.log

# Uvicorn-Logs (Container)
# (außerhalb der Sandbox:)
docker logs -f vera-backend
```

### Python/FastAPI
```bash
# Python REPL
python

# FastAPI Shell
python -m backend.main

# Datenbank-Migration
alembic upgrade head

# Tests
pytest
```

### Git & Code
```bash
git status
git log --oneline
git diff

# Code editieren
vim backend/main.py
nano config/settings.py
```

## 🔥 Hot Tips

**PowerShell in der Sandbox:**
```bash
pwsh -NoProfile -Command "Get-ChildItem /app"
```

**Datenbank direkt abfragen:**
```bash
sqlite3 /app/data/vera.db "SELECT * FROM documents LIMIT 5;"
```

**Dateien zwischen Host & Container kopieren:**
```powershell
# Host → Container
docker cp test.pdf vera-backend:/app/data/

# Container → Host
docker cp vera-backend:/app/data/vera.db ./backup.db
```

**Container neu starten (schnell):**
```powershell
docker restart vera-backend
```

## ⚙️ Config ändern

1. **In der Sandbox:**
   ```bash
   nano /app/config/settings.py
   ```

2. **Container neu starten** (damit Änderungen wirksam werden):
   ```powershell
   docker restart vera-backend
   ```

## 🐛 Troubleshooting

**Container läuft nicht?**
```powershell
docker ps -a | Select-String vera
docker logs vera-backend --tail 50
```

**Port belegt?**
```powershell
netstat -ano | findstr :8000
```

**Alles zurücksetzen:**
```powershell
cd C:\Jarvix\vera-office\docker
docker-compose down -v  # -v löscht auch Volumes (Achtung: Daten weg!)
docker-compose up -d --build
```
