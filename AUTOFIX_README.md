# 🚀 VERA Auto-Fix Pipeline — Quick Start

## Was ist das?

Ein vollautomatischer Bug-Fix-Loop für VERA Office:

**User meldet Bug via Telegram** → **VERA analysiert** → **Auto-Fix Agent bereitet vor** → **Coding Agent fixt** → **User bekommt Update**

---

## ⚡ Quick Start

### 1. Auto-Fix Agent starten
```powershell
cd C:\Jarvix\vera-office
.\start_autofix.ps1
```

Das war's! Der Agent läuft jetzt und:
- ✅ Pollt `data/bug_queue/` alle 30 Sekunden
- ✅ Erstellt Fix-Briefings für neue Bugs
- ✅ Sendet Status-Updates an User via Telegram

### 2. Telegram Bot (falls noch nicht läuft)
```powershell
cd backend/services
python telegram_bot.py
```

---

## 📋 Wie funktioniert's?

### User-Perspektive (Telegram)
1. User: "OCR erkennt keine Umlaute"
2. Bot: "🐛 Bug #42 erfasst. VERA analysiert..."
3. Bot: "✅ Analyse fertig (KI): Modul: ocr, Severity: high"
4. *(30 Sekunden später)*
5. Bot: "🔬 Bug #42 — Auto-Fix wird vorbereitet"
6. Bot: "✅ Fix-Plan erstellt. Coding-Agent wird nun Fix implementieren."
7. *(später)*
8. Bot: "✅ Bug #42 — Fix deployed!"

### User kann Rückfragen beantworten
- Bot: "❓ Tritt der Fehler nur bei Rechnungen auf?"
- User: *(Reply)* "Ja, nur bei Rechnungen"
- Bot: "✅ Deine Antwort wurde gespeichert."

→ Die Antwort wird automatisch in die Fix-Task eingetragen!

---

## 📁 Was passiert im Hintergrund?

```
data/bug_queue/
├── bug_0042_20260306_073000.json    ← User-Bug (Javix Bridge)
│                                     ↓ (Auto-Fix Agent liest)
├── in_progress/                      ← Bug wird bearbeitet
│   └── bug_0042_20260306_073000.json
│
└── fix_tasks/                        ← Coding Agent arbeitet hier
    └── fix_task_0042_20260306_073100.json
        ├── Bug-Analyse
        ├── Code-Context (200 Zeilen/File)
        ├── Fix-Hinweise
        └── User-Replies
```

---

## 🔧 Konfiguration

### Telegram Bot Token
```yaml
# config/vera.yaml
telegram:
  bot_token: "YOUR_BOT_TOKEN"
  enabled: true
```

### Poll-Intervall anpassen
```python
# backend/services/autofix_agent.py
POLL_INTERVAL = 30  # Sekunden (default: 30)
```

### Max. Code-Zeilen pro Datei
```python
# backend/services/autofix_agent.py
MAX_CODE_LINES_PER_FILE = 200  # default: 200
```

---

## 🛠️ Troubleshooting

### Agent startet nicht?
```powershell
# Dependencies installieren
pip install requests pyyaml

# Manual start für Debug-Output
python backend/services/autofix_agent.py
```

### Keine Telegram-Nachrichten?
1. Prüfe `config/vera.yaml` → `telegram.bot_token` gesetzt?
2. Ist `telegram.enabled: true`?
3. Teste manuell: `python backend/services/telegram_bot.py`

### User-Replies funktionieren nicht?
- User muss auf Bot-Nachricht **antworten** (Telegram Reply-Feature)
- Bot-Nachricht muss "Bug #XX" oder "Ticket #XX" enthalten

---

## 📊 Monitoring

### Logs ansehen
```powershell
# Auto-Fix Agent
cat logs/autofix_agent.log

# Letzte 20 Zeilen
Get-Content logs/autofix_agent.log -Tail 20
```

### Queue Status
```powershell
# Pending (wird bearbeitet)
ls data/bug_queue/bug_*.json

# In Progress
ls data/bug_queue/in_progress/

# Fix Tasks (bereit für Coding Agent)
ls data/bug_queue/fix_tasks/
```

### Database
```powershell
# SQLite Browser oder
sqlite3 data/feedback.db "SELECT id, message, status FROM feedback ORDER BY id DESC LIMIT 10"
```

---

## 📖 Mehr Infos

**Vollständige Dokumentation:**  
[docs/AUTOFIX_PIPELINE.md](docs/AUTOFIX_PIPELINE.md)

**Komponenten:**
- `backend/services/autofix_agent.py` — Auto-Fix Daemon
- `backend/services/telegram_bot.py` — Telegram Bot (erweitert)
- `start_autofix.ps1` — Start-Script

---

## ✅ Checkliste

- [ ] Auto-Fix Agent läuft (`.\start_autofix.ps1`)
- [ ] Telegram Bot läuft (`python backend/services/telegram_bot.py`)
- [ ] `config/vera.yaml` → `telegram.bot_token` gesetzt
- [ ] Erste Test-Nachricht via Telegram gesendet
- [ ] `data/bug_queue/fix_tasks/` wird befüllt

---

**Version:** 1.0.0  
**Status:** ✅ Production Ready  
**Support:** Boris Reimers (@ReyBonnet)
