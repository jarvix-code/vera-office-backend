# VERA Office - Produktive Sandbox

## Was wurde installiert?

Die VERA Sandbox ist **vollständig ausgestattet** - keine Zeit verschwenden mit Setup:

### ✅ Shell & Skripting
- **PowerShell Core** (`pwsh`) - volle PS-Kompatibilität in Linux
- **Bash** (Standard)
- Aliases: `md` (mkdir), `cls` (clear), `ll` (ls -lah), `ps1` (pwsh)

### ✅ Entwickler-Tools
- **vim**, **nano** - Text-Editoren
- **git** - Version Control
- **curl**, **wget** - HTTP-Clients
- **jq** - JSON-Parser
- **tree** - Directory-Visualizer

### ✅ System-Tools
- **htop** - Prozess-Monitor
- **less** - File-Viewer
- **net-tools**, **iputils-ping** - Netzwerk-Debugging
- **unzip** - Archive

---

## 🚀 Schnellstart (3 Befehle)

```powershell
cd C:\Jarvix\vera-office
.\start-vera.ps1
docker exec -it vera-backend bash
```

**Fertig!** Du bist in der Sandbox mit allen Tools.

---

## 📖 Dokumentation

- **QUICK_START.md** → Übersicht & wichtigste Befehle
- **SANDBOX_CHEATSHEET.md** → Alle Befehle & Tipps
- **README_SANDBOX.md** (diese Datei) → Konzept & Setup

---

## 🎯 Typische Workflows

### 1️⃣ Backend-Code inspizieren
```bash
cd /app/backend
ll
cat main.py
vim routers/documents.py
```

### 2️⃣ API testen
```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/documents | jq .
```

### 3️⃣ Datenbank prüfen
```bash
sqlite3 /app/data/vera.db "SELECT * FROM documents;"
```

### 4️⃣ PowerShell-Skript ausführen
```bash
pwsh /app/scripts/analyze.ps1
```

### 5️⃣ Logs überwachen
```bash
tail -f /app/logs/vera.log
```

---

## 🔧 Konfiguration ändern

**In der Sandbox:**
```bash
nano /app/config/settings.py
exit
```

**Container neu starten:**
```powershell
docker restart vera-backend
```

---

## 📦 Persistente Daten

Alles in `/app/data/` bleibt nach Container-Neustart erhalten:
- `vera.db` → Datenbank
- `documents/` → Hochgeladene Dateien
- `cache/` → OCR-Cache

**Backup erstellen:**
```powershell
docker cp vera-backend:/app/data ./backup-$(Get-Date -Format yyyyMMdd)
```

---

## 🛑 Sandbox stoppen

```powershell
cd C:\Jarvix\vera-office\docker
docker-compose down
```

**Oder nur pausieren (schneller Neustart):**
```powershell
docker stop vera-backend
docker start vera-backend
```

---

## 🐛 Troubleshooting

**Container startet nicht?**
```powershell
docker logs vera-backend --tail 100
```

**Port 8000 belegt?**
```powershell
netstat -ano | findstr :8000
```

**Kompletter Reset (Achtung: löscht Daten!):**
```powershell
cd C:\Jarvix\vera-office\docker
docker-compose down -v
docker-compose up -d --build
```

---

## 💡 Pro-Tipps

**PowerShell One-Liner in der Sandbox:**
```bash
pwsh -NoProfile -Command "Get-ChildItem /app | Format-Table"
```

**Python-Code direkt ausführen:**
```bash
python -c "from backend.ocr import process_pdf; print(process_pdf('/app/data/test.pdf'))"
```

**Mehrere Terminals gleichzeitig:**
```powershell
# Terminal 1: Backend-Logs
docker logs -f vera-backend

# Terminal 2: Sandbox-Shell
docker exec -it vera-backend bash

# Terminal 3: API-Requests
curl http://localhost:8000/api/v1/documents
```

---

**Die Sandbox ist bereit. Viel Erfolg beim Testen! 🎯**
