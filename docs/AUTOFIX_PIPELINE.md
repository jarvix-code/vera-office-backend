# VERA Auto-Fix Pipeline

## Übersicht

Die Auto-Fix Pipeline automatisiert den Weg vom User-Bug-Report bis zum fertigen Fix:

```
User → Telegram → VERA LLM → Bug Queue → Auto-Fix Agent → Coding Agent → Fix
         ↓           ↓                         ↓
    feedback.db  bug_*.json              fix_task_*.json
```

## Komponenten

### 1. Telegram Bot (`telegram_bot.py`)
- Empfängt Bug-Reports von Usern
- Speichert in `feedback.db`
- Ruft VERA LLM zur Analyse auf
- **NEU:** Reply-Handler für User-Rückfragen

### 2. Bug Analyzer (`bug_analyzer.py`)
- Analysiert Bug-Text mit VERA's Mistral 7B LLM
- Identifiziert: Modul, Severity, betroffene Dateien
- Fallback auf regelbasierte Analyse

### 3. Javix Bridge (`javix_bridge.py`)
- Erstellt strukturierte JSON-Files in `data/bug_queue/`
- Format: `bug_NNNN_timestamp.json`

### 4. **Auto-Fix Agent (`autofix_agent.py`)** ⭐ NEU
- **Daemon** der alle 30s die Queue pollt
- Liest betroffene Code-Dateien (max 200 Zeilen/File)
- Erstellt Fix-Briefings in `data/bug_queue/fix_tasks/`
- Verschiebt Original-Bug nach `in_progress/`
- **Telegram-Rückkanal** für Status-Updates

### 5. Coding Agent (Javix/Claude Code)
- Liest `fix_task_*.json`
- Implementiert Fix
- Deployed & testet

---

## Verzeichnisstruktur

```
data/
├── bug_queue/
│   ├── bug_*.json              ← Neue Bugs (Javix Bridge)
│   ├── in_progress/            ← Wird bearbeitet
│   ├── fix_tasks/              ← Fix-Briefings für Coding Agent
│   │   └── fix_task_*.json     ← Code-Context + Instructions
│   └── backups/                ← Automatische Backups
└── feedback.db                 ← User-Feedback + Replies
```

---

## Datenformate

### `bug_NNNN_timestamp.json`
```json
{
  "version": 1,
  "ticket_id": 42,
  "timestamp": "2026-03-06T07:30:00",
  "status": "pending",
  "original_text": "OCR erkennt keine Umlaute",
  "user": {
    "id": 123456,
    "username": "test_user",
    "name": "Max"
  },
  "analysis": {
    "module": "ocr",
    "severity": "high",
    "title": "OCR Umlaut-Erkennung fehlerhaft",
    "affected_files": ["backend/core/ocr_engine.py"],
    "fix_hint": "Prüfe Tesseract language config"
  }
}
```

### `fix_task_NNNN_timestamp.json`
```json
{
  "version": 1,
  "created_at": "2026-03-06T07:31:00",
  "ticket_id": 42,
  "bug": {
    "original_text": "...",
    "user": {...}
  },
  "analysis": {...},
  "code_context": [
    {
      "path": "backend/core/ocr_engine.py",
      "exists": true,
      "lines": 450,
      "content": "...",
      "truncated": true
    }
  ],
  "fix_instructions": {
    "module": "ocr",
    "severity": "high",
    "title": "...",
    "possible_cause": "...",
    "fix_hint": "...",
    "reproduction_steps": [...]
  },
  "status": "pending",
  "user_replies": [
    {
      "timestamp": "2026-03-06T08:00:00",
      "text": "Es passiert nur bei ä, ö, ü",
      "user": {...}
    }
  ]
}
```

---

## Telegram-Rückkanal

### Funktion im Auto-Fix Agent
```python
send_to_user(telegram_user_id, message_text)
```

### Beispiel-Nachrichten
```python
# Status Update
send_to_user(user_id, 
    "🔬 Bug #42 — Auto-Fix wird vorbereitet\n\n"
    "VERA analysiert den Code..."
)

# Rückfrage
send_to_user(user_id,
    "❓ Bug #42 — Rückfrage\n\n"
    "Tritt der Fehler nur bei Rechnungen oder auch bei anderen Dokumenten auf?"
)

# Fix deployed
send_to_user(user_id,
    "✅ Bug #42 — Fix deployed!\n\n"
    "Die Umlaut-Erkennung wurde verbessert."
)
```

### User-Replies
User können auf Bot-Nachrichten **direkt antworten** (Telegram Reply):

1. User schickt Reply → `telegram_bot.py` erkennt Ticket-#
2. Reply wird gespeichert:
   - In `feedback.db` (Spalte `replies` als JSON)
   - In `fix_task_NNNN.json` (Array `user_replies`)
3. Coding Agent kann Replies beim Fix berücksichtigen

---

## Starten

### Auto-Fix Agent
```powershell
# Option 1: Mit Logging
.\start_autofix.ps1

# Option 2: Debug (Ausgabe in Console)
.\start_autofix.ps1 -Debug
```

### Telegram Bot
```powershell
cd backend/services
python telegram_bot.py
```

---

## Workflow-Beispiel

### 1. User meldet Bug via Telegram
```
User: "OCR erkennt keine Umlaute bei Rechnungen"
```

### 2. Telegram Bot analysiert
```
Bot → feedback.db (Ticket #42)
Bot → bug_analyzer.py (LLM-Analyse)
Bot → javix_bridge.py (bug_0042_timestamp.json)
Bot → User: "✅ Analyse fertig (KI): Modul: ocr, Severity: high"
```

### 3. Auto-Fix Agent verarbeitet (nach max. 30s)
```
autofix_agent.py:
  1. Findet bug_0042_*.json
  2. Liest backend/core/ocr_engine.py (200 Zeilen)
  3. Erstellt fix_task_0042_*.json
  4. Verschiebt Bug → in_progress/
  5. Telegram: "✅ Fix-Plan erstellt. Coding-Agent wird nun Fix implementieren."
```

### 4. User schickt Rückfrage (Reply auf Bot-Nachricht)
```
User (Reply): "Es passiert nur bei ä, ö, ü"

telegram_bot.py:
  - Erkennt Ticket #42 aus Original-Nachricht
  - Speichert Reply in feedback.db + fix_task_0042.json
  - Bot: "✅ Deine Antwort zu Bug #42 wurde gespeichert."
```

### 5. Coding Agent implementiert Fix
```
Javix/Claude Code:
  - Liest fix_task_0042.json
  - Analysiert Code + User-Antwort
  - Implementiert Fix
  - Testet
  - Committed
```

### 6. Finale Status-Updates
```
autofix_agent.py → User:
  "✅ Bug #42 — Fix deployed! Die Umlaut-Erkennung wurde verbessert."
```

---

## Sicherheit

### Backups
Vor jedem File-Edit erstellt der Agent automatisch Backups in `data/bug_queue/backups/`.

### Kein destruktiver Code
Der Auto-Fix Agent schreibt **niemals** in den Production-Code. Er:
- Liest nur Code-Dateien
- Erstellt nur JSON-Briefings
- Der eigentliche Fix wird vom Coding Agent gemacht (unter Aufsicht)

### Telegram-Authentifizierung
- Bot-Token aus `config/vera.yaml`
- User-IDs werden verifiziert
- Admin-Befehle sind geschützt

---

## Monitoring & Debugging

### Logs
```powershell
# Auto-Fix Agent Log
cat logs/autofix_agent.log

# Telegram Bot Log
# (in Console, wenn direkt gestartet)
```

### Queue Status
```powershell
# Pending bugs
ls data/bug_queue/bug_*.json

# In Progress
ls data/bug_queue/in_progress/

# Fix Tasks (ready for Coding Agent)
ls data/bug_queue/fix_tasks/
```

### Database
```sql
-- Offene Tickets mit Replies
SELECT id, message, replies 
FROM feedback 
WHERE status = 'open' AND replies != '[]';
```

---

## Erweiterungen (Future)

1. **Auto-Assignment**: Fix-Tasks automatisch an verfügbare Coding Agents zuweisen
2. **Priority Queue**: Critical Bugs bevorzugt bearbeiten
3. **Fix Verification**: Automated tests vor Deployment
4. **User Feedback Loop**: "War der Fix erfolgreich?" → Ja/Nein Button
5. **Analytics Dashboard**: Bug-Trends, häufigste Module, Fix-Zeiten

---

## Troubleshooting

### Auto-Fix Agent startet nicht
```powershell
# Python-Version prüfen
python --version  # Muss 3.10+

# Dependencies prüfen
pip install requests pyyaml

# Manual start für Debug
python backend/services/autofix_agent.py
```

### Telegram-Nachrichten kommen nicht an
```yaml
# config/vera.yaml prüfen
telegram:
  bot_token: "YOUR_BOT_TOKEN"  # Muss gesetzt sein
  enabled: true
```

### User-Replies werden nicht erkannt
- Prüfe ob User wirklich auf Bot-Nachricht antwortet (Telegram Reply-Feature)
- Ticket-# muss in Bot-Nachricht enthalten sein (Format: "Bug #42" oder "Ticket #42")

---

**Status:** ✅ Production Ready  
**Version:** 1.0.0  
**Last Updated:** 2026-03-06
