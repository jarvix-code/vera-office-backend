# QUICK FIX - VERA QM Parser Classifier

## Problem
LLM returns empty string → All PDFs classified as "sonstige"

## Root Cause
Bad stop-token `["\n"]` cuts off LLM response before it can answer.

## Solution
Replace prompt with Few-Shot version + fix stop-tokens.

---

## OPTION 1: Use Fixed Version (Recommended)

Already created: `simple_loop_parser_FIXED.py`

**Run:**
```powershell
cd C:\Jarvix\vera-office\backend
$env:PYTHONIOENCODING="utf-8"
python simple_loop_parser_FIXED.py
```

**Changes:**
- ✅ Few-Shot prompt (CLASSIFIER_PROMPT)
- ✅ Better stop-tokens: `["Dokument", "BEISPIEL"]` instead of `["\n"]`
- ✅ Increased max_tokens: 30 instead of 20
- ✅ Remove trailing punctuation from response
- ✅ Output: `extraction_report_fixed.json`

---

## OPTION 2: Manual Patch (If you want to fix original file)

**File:** `simple_loop_parser.py`

### Step 1: Replace CLASSIFIER_PROMPT (Line ~18)

**OLD:**
```python
CLASSIFIER_PROMPT = """Klassifiziere dieses Dokument:

Typen:
- checkliste: Hat Ja/Nein-Fragen, Verantwortliche, Erledigungs-Status
- arbeitsanweisung: Hat nummerierte Schritte, Bullet-Points, Prozess-Beschreibung
- sonstige: Alles andere

Text:
{text}

Antworte NUR mit dem Typ (ohne Erklärung):"""
```

**NEW:**
```python
CLASSIFIER_PROMPT = """Du bist ein QM-Dokument-Classifier für Zahnarztpraxen.

BEISPIEL 1 - Typ: checkliste
Dokument: "Datenschutz Checkliste
□ Datenschutzbeauftragter benannt? [Ja/Nein]
□ Verarbeitungsverzeichnis erstellt? [Ja/Nein]
Verantwortlich: Praxisinhaber"
Antwort: checkliste

BEISPIEL 2 - Typ: arbeitsanweisung
Dokument: "Röntgen-Durchführung
1. Vorbereitung
   - Patient aufklären
   - Schutzkleidung anlegen
2. Durchführung
   - Gerät einschalten
   - Position einstellen"
Antwort: arbeitsanweisung

BEISPIEL 3 - Typ: sonstige
Dokument: "BLZK Newsletter 02/2024
Wichtige Informationen zur neuen GOZ-Regelung..."
Antwort: sonstige

JETZT DU:
Dokument: {text}
Antwort:"""
```

### Step 2: Fix classify_document() function (Line ~54)

**OLD:**
```python
def classify_document(text, llm):
    """Classify document type"""
    prompt = CLASSIFIER_PROMPT.format(text=text)
    response = llm.create_completion(
        prompt=prompt,
        max_tokens=20,
        temperature=0.1,
        stop=["\n"]
    )
    typ = response["choices"][0]["text"].strip().lower()
    
    if "checkliste" in typ:
        return "checkliste"
    elif "arbeitsanweisung" in typ or "procedure" in typ:
        return "arbeitsanweisung"
    else:
        return "sonstige"
```

**NEW:**
```python
def classify_document(text, llm):
    """Classify document type"""
    prompt = CLASSIFIER_PROMPT.format(text=text)
    response = llm.create_completion(
        prompt=prompt,
        max_tokens=30,  # FIXED: Increased from 20
        temperature=0.1,
        stop=["Dokument", "BEISPIEL"]  # FIXED: Better stop tokens
    )
    typ = response["choices"][0]["text"].strip().lower()
    
    # FIXED: Remove trailing punctuation
    typ = typ.rstrip('.,:;')
    
    if "checkliste" in typ:
        return "checkliste"
    elif "arbeitsanweisung" in typ or "procedure" in typ:
        return "arbeitsanweisung"
    else:
        return "sonstige"
```

---

## Expected Results

### Before Fix:
```
Total:          447
Checklisten:    0
Arbeitsanw.:    0 (0 steps)
Sonstige:       447
```

### After Fix (Projected):
```
Total:          447
Checklisten:    22-45   (~5-10%)
Arbeitsanw.:    45-90   (~10-20%, with 150-300 steps)
Sonstige:       312-380 (~70-85%)
```

**Note:** Most PDFs (70-85%) SHOULD be "sonstige" because they're newsletters, laws, and reference material. This is CORRECT!

---

## Verification

After running fixed parser:

1. **Check DB:**
```powershell
python -c "import sqlite3; conn = sqlite3.connect('C:/Jarvix/vera-office/data/vera.db'); print('Processes:', conn.execute('SELECT COUNT(*) FROM qm_processes').fetchone()[0])"
```

2. **Check Report:**
```powershell
cat C:\Jarvix\vera-office\backend\extraction_report_fixed.json | ConvertFrom-Json | Select-Object -ExpandProperty stats
```

3. **Sample Results:**
```powershell
python -c "import json; report = json.load(open('C:/Jarvix/vera-office/backend/extraction_report_fixed.json', encoding='utf-8')); [print(f\"{r['file']}: {r['type']}\") for r in report['results'][:20]]"
```

---

## Time Estimate

- **Fix code:** 5 minutes
- **Run parser:** 2-4 hours (447 PDFs × ~15-20s each)
- **Verify results:** 5 minutes

**Total:** ~2.5-4.5 hours

---

## Safety

- ✅ No data loss (can always re-run)
- ✅ Original file untouched (if using FIXED version)
- ✅ New report file (extraction_report_fixed.json)
- ✅ DB has CREATE TABLE IF NOT EXISTS (safe)

---

## Rollback

If something goes wrong:

1. **Stop parser:** Ctrl+C
2. **Delete bad data:**
```powershell
python -c "import sqlite3; conn = sqlite3.connect('C:/Jarvix/vera-office/data/vera.db'); conn.execute('DELETE FROM qm_processes'); conn.commit()"
```
3. **Re-run with original version**

---

**Created by:** Javix (Sub-Agent qm-classifier-fix)  
**Date:** 2026-03-28  
**Status:** Ready to deploy
