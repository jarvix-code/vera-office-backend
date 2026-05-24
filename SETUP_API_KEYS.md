# VERA Office - API Key Setup Guide

## Warum braucht VERA API Keys?

VERA nutzt ein **Hybrid-LLM-Setup** für optimale Performance:

- **Fast Cloud LLM (GPT-4o-mini)**: Für User-facing Tasks (Chat, Onboarding)
  - Response-Zeit: < 1 Sekunde
  - Kosten: ~0.15 USD / 1M Tokens (sehr günstig)
  - **Benötigt API Key**

- **Local LLM (Mistral 7B)**: Für Background-Tasks (Dokument-Klassifikation)
  - Response-Zeit: 30s+ (akzeptabel für Background)
  - Kosten: 0 USD (läuft lokal)
  - **Kein API Key benötigt**

## Was passiert OHNE API Key?

VERA funktioniert **komplett offline** - alle Tasks nutzen dann Local LLM:
- ✅ Chat funktioniert (mit Local LLM, etwas langsamer)
- ✅ Klassifikation funktioniert (Local LLM)
- ✅ Alle Features verfügbar

**ABER:** Chat-Response ist langsamer (15-30s statt < 1s).

## OpenAI API Key Setup (Empfohlen)

### 1. API Key besorgen

1. Gehe zu: https://platform.openai.com/signup
2. Erstelle einen Account (falls noch nicht vorhanden)
3. Navigiere zu: https://platform.openai.com/api-keys
4. Klicke: **"Create new secret key"**
5. Name: "VERA Office"
6. Kopiere den Key: `sk-proj-...` (wird nur EINMAL angezeigt!)

**Kosten:** OpenAI hat Pay-as-you-go Pricing:
- GPT-4o-mini: $0.15 / 1M Input Tokens, $0.60 / 1M Output Tokens
- Geschätzte monatliche Kosten für kleine Praxis: **< 5 USD/Monat**

### 2. API Key in VERA eintragen

**Option A: Environment Variable (Empfohlen)**

Erstelle `.env` Datei im VERA-Verzeichnis:

```bash
# .env
OPENAI_API_KEY=sk-proj-DEIN-API-KEY-HIER
```

**Option B: Config-Datei**

Öffne `config/vera.yaml` und trage ein:

```yaml
fast_llm:
  provider: "openai"
  model: "gpt-4o-mini"
  api_key: "sk-proj-DEIN-API-KEY-HIER"  # ⚠️ NICHT committen!
```

⚠️ **Sicherheitshinweis:** Wenn du Config-Datei nutzt, NIEMALS in Git committen!

### 3. VERA neu starten

```bash
# Windows
cd C:\VERA-Office
.\start-vera.bat

# Linux/Mac
cd /opt/vera-office
./start-vera.sh
```

### 4. Verifizieren

Öffne VERA Chat und teste:

```
User: Hallo VERA!
VERA: [sollte < 2s antworten]
```

Oder teste via Test-Script:

```bash
python test_llm_router.py
```

Expected Output:
```
✅ Hybrid Mode Active:
   - User-facing tasks (chat) → Fast Cloud LLM
   - Background tasks (classification) → Local LLM
```

## Alternative: Anthropic Claude (Future)

**Status:** In Vorbereitung, noch nicht implementiert.

Wenn du statt OpenAI lieber Anthropic Claude Haiku nutzen willst:

1. Hole dir einen API Key: https://console.anthropic.com/
2. Setze in `.env`:
   ```bash
   FAST_LLM_PROVIDER=anthropic
   FAST_LLM_MODEL=claude-3-haiku-20240307
   FAST_LLM_API_KEY=sk-ant-...
   ```

**Claude Haiku Kosten:** $0.25 / 1M Input Tokens, $1.25 / 1M Output Tokens

## Troubleshooting

### "Fast LLM not available (no API key)"

**Problem:** API Key nicht gesetzt oder ungültig.

**Lösung:**
1. Prüfe `.env` Datei: `OPENAI_API_KEY=sk-proj-...` vorhanden?
2. Prüfe Key-Format: Startet mit `sk-proj-` (neue Keys) oder `sk-` (alte Keys)
3. Teste Key manuell:
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer sk-proj-DEIN-KEY"
   ```

### "openai package not installed"

**Problem:** Python-Dependency fehlt.

**Lösung:**
```bash
pip install openai
# Oder für Development:
pip install -r requirements.txt
```

### Chat ist langsam trotz API Key

**Problem:** Fast LLM wird nicht genutzt.

**Lösung:**
1. Prüfe Logs: `logs/vera.log` → "Chat routed to: OpenAI GPT-4o-mini"
2. Wenn "Local LLM": API Key nicht erkannt → prüfe `.env`
3. Test-Script laufen lassen: `python test_llm_router.py`

### "Invalid API Key"

**Problem:** Key ist abgelaufen oder ungültig.

**Lösung:**
1. Gehe zu: https://platform.openai.com/api-keys
2. Prüfe Key-Status (aktiv/deaktiviert)
3. Erstelle neuen Key falls nötig

### Rate Limit Exceeded

**Problem:** Zu viele Anfragen pro Minute.

**Lösung:**
1. OpenAI Free Tier: 3 requests/min, 200 requests/day
2. Lösung: Upgrade auf Pay-as-you-go ($5 Mindestguthaben)
3. Oder: Nutze Local LLM (kein Rate Limit)

## FAQ

### Q: Werden meine Dokumente an OpenAI geschickt?

**A:** NEIN! Nur Chat-Nachrichten gehen zu OpenAI.

Dokument-Klassifikation läuft **IMMER lokal** (Mistral 7B):
- OCR-Text verlässt NIEMALS das Gerät
- Nur User-Chat-Nachrichten nutzen Cloud LLM
- Sensitive Dokumente bleiben lokal

### Q: Was kostet mich VERA pro Monat?

**A:** Geschätzt **< 5 USD/Monat** (kleine Praxis):
- 100 Chat-Messages/Tag: ~0.01 USD/Tag = 0.30 USD/Monat
- Onboarding (einmalig): ~0.05 USD
- Total: **< 5 USD/Monat**

Für Vergleich: Paperless-ngx ist komplett offline (0 USD), aber auch viel langsamer.

### Q: Kann ich VERA komplett offline nutzen?

**A:** JA! VERA funktioniert **OHNE API Key**:
- Alle Tasks nutzen Local LLM (Mistral 7B)
- Chat-Response: 15-30s statt < 1s
- Klassifikation: unverändert (läuft eh lokal)

### Q: Welcher Provider ist besser: OpenAI oder Anthropic?

**A:** Für VERA: **OpenAI GPT-4o-mini** (aktuell):
- ✅ Günstiger ($0.15/M vs. $0.25/M)
- ✅ Schneller (< 500ms)
- ✅ Gute Deutsch-Unterstützung
- ✅ Einfachere API

Anthropic Claude Haiku:
- ✅ Bessere Context-Länge (200k Tokens)
- ❌ Teurer
- ⏳ Noch nicht implementiert (geplant)

## Support

Bei Problemen:
1. Prüfe Logs: `logs/vera.log`
2. Teste Routing: `python test_llm_router.py`
3. Erstelle Issue: https://github.com/boris-vera/vera-office/issues
4. Telegram: @VERAOfficeSupport

---

**TL;DR:**
1. Hole dir OpenAI API Key: https://platform.openai.com/api-keys
2. Trage ein in `.env`: `OPENAI_API_KEY=sk-proj-...`
3. VERA neu starten
4. Chat sollte jetzt < 2s antworten 🚀
