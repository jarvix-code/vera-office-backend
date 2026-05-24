## Autonomous Execution Rules

1. Do NOT ask for confirmation between steps. Complete the task end-to-end.
2. Only ask BEFORE starting if the scope is genuinely unclear.
3. Only stop mid-task if you're about to do something destructive outside the original scope.
4. If you hit a blocker: try to solve it. If you can't solve it, work around it. If you can't work around it, document it and move to the next subtask.
5. Define "done" clearly at the start, then work until you reach it.
6. Never output "I will now implement X" and then stop. Just implement X.
7. Bei Fehlern: selbst fixen, nicht fragen. Fehler in `error_reporter.py` loggen und per Telegram melden. Bei wiederholtem Scheitern: weiter zum nächsten Punkt.
8. Health-Checks alle 30 Min selbstständig durchführen: VERA-Server, LLM-Status, Pipeline-Status.
9. Bei Ausfall eines Systems: selbstständig neu starten, nicht auf Anweisung warten.
10. Alle Änderungen in `vera.db` dokumentieren, KEINE neuen MD-Dateien anlegen.

---

# VERA Office

VERA (Virtual Executive & Research Assistant) — AI-powered office automation system.

## Architecture

- **Backend**: FastAPI + LLM pipeline
- **Database**: `vera.db` (SQLite)
- **Error Reporting**: `error_reporter.py` → Telegram alerts
- **Admin UI**: `vera-admin/`

## Key Services

| Service | Notes |
|---------|-------|
| VERA Server | Main API + LLM pipeline |
| LLM Status | Model inference backend |
| Pipeline Status | Document/task processing pipeline |

## Error Handling

All errors go through `error_reporter.py` and are:
1. Logged to `vera.db`
2. Sent via Telegram notification

## Rules for Claude

1. **NEVER** modify `vera.db` schema without explicit instruction
2. **ALWAYS** use `error_reporter.py` for error logging
3. **ALWAYS** test pipeline after changes
4. **NEVER** expose credentials or API keys in logs
