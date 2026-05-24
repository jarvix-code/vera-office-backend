# VERA Escalation Workflow - Developer Queue

**Boris' Requirement:** "Wenn VERA gar nicht weiterkommt, muss VERA das Entwickler-Team fragen"

---

## 🎯 KONZEPT

### Warum Escalation?

**Situationen:**
1. **User + VERA unsicher** → Keiner weiß was das ist
2. **OCR-Qualität schlecht** → Text unleserlich
3. **Neuer Dokumenttyp** → Noch nie gesehen
4. **Fehlerhafte Klassifikation** → System-Problem

**Lösung:** Developer Queue
- Developer reviewt schwierige Fälle
- Erstellt neue Kategorien/Regeln
- System-Update → Alle Praxen profitieren!

---

## 🔄 WORKFLOW

### 1. User Option: "Ich bin auch unsicher"

**Szenario:**
```
VERA: "Hey Boris, was ist das?"

Boris schaut Dokument an:
"Hmm... keine Ahnung. Das ist mir auch unklar."

Boris klickt: [Ich bin auch unsicher]
```

**System-Aktion:**
```python
# Dokument in Developer Queue
doc.classification_status = "needs_dev_review"
doc.escalated_at = datetime.now()
doc.escalated_by = "Boris"
doc.user_comment = "Ich bin auch unsicher"

# Notification
notify_user(
    "Okay, ich frage das Entwickler-Team. "
    "Dokument kommt in die Review-Queue."
)
```

### 2. Dokument in Queue

**Developer Queue View:**
```
📋 Entwickler-Review Queue (15 Dokumente)

┌─────────────────────────────────────────────────┐
│ 📄 unbekanntes_dokument.pdf                     │
│    Escalated by: Boris                          │
│    Date: 2026-03-28 14:30                       │
│    User comment: "Ich bin auch unsicher"        │
│    Confidence: 0.42                             │
│                                                  │
│    [📄 Ansehen]  [Review]                       │
├─────────────────────────────────────────────────┤
│ 📄 schlechte_qualitaet.pdf                      │
│    Escalated by: System (OCR Error)             │
│    Date: 2026-03-28 15:12                       │
│    Error: "Text unleserlich (Confidence 0.15)"  │
│                                                  │
│    [📄 Ansehen]  [Review]                       │
└─────────────────────────────────────────────────┘
```

### 3. Developer Review

**Developer öffnet Dokument:**
```
╔══════════════════════════════════════════════════╗
║  Developer Review                        [X]     ║
║  ─────────────────────────────────────────────   ║
║                                                   ║
║  Dokument: unbekanntes_dokument.pdf              ║
║  Escalated by: Boris                             ║
║  Date: 2026-03-28 14:30                          ║
║                                                   ║
║  User Comment:                                   ║
║  "Ich bin auch unsicher"                         ║
║                                                   ║
║  ┌──────────────────────────────────────────┐   ║
║  │ [PDF Preview]                            │   ║
║  └──────────────────────────────────────────┘   ║
║                                                   ║
║  OCR Text:                                       ║
║  ┌──────────────────────────────────────────┐   ║
║  │ [Text anzeigen]                          │   ║
║  └──────────────────────────────────────────┘   ║
║                                                   ║
║  Developer Decision:                             ║
║  ○ Neue Kategorie erstellen                      ║
║  ○ Regel hinzufügen                              ║
║  ○ OCR-Problem                                   ║
║  ○ Training nötig                                ║
║                                                   ║
╚══════════════════════════════════════════════════╝
```

### 4a. Decision: Neue Kategorie

**Developer wählt: "Neue Kategorie erstellen"**
```
╔══════════════════════════════════════════════════╗
║  Neue Kategorie erstellen                        ║
║                                                   ║
║  Kategorie-Name:                                 ║
║  ┌──────────────────────────────────────────┐   ║
║  │ Prüfbericht (Qualitätsmanagement)       │   ║
║  └──────────────────────────────────────────┘   ║
║                                                   ║
║  Erklärung:                                      ║
║  ┌──────────────────────────────────────────┐   ║
║  │ Das ist ein Prüfbericht für das QM-     │   ║
║  │ System. Wird von externen Prüfern       │   ║
║  │ erstellt bei jährlicher Qualitätsprüfung│   ║
║  └──────────────────────────────────────────┘   ║
║                                                   ║
║  Developer Notes (intern):                       ║
║  ┌──────────────────────────────────────────┐   ║
║  │ Neue Dokumentklasse für QM-Modul.       │   ║
║  │ Pattern: "Prüfbericht" + Jahr            │   ║
║  └──────────────────────────────────────────┘   ║
║                                                   ║
║  [Kategorie erstellen & Dokument klassifizieren] ║
║                                                   ║
╚══════════════════════════════════════════════════╝
```

**System-Aktion:**
```python
# 1. Create new category
category_info = extract_category_from_explanation(
    "Prüfbericht für QM-System, von externen Prüfern"
)
add_new_category(
    category_info,
    user_id=0,  # System/Developer
    user_name="Developer"
)

# 2. Classify document
doc.category = "Prüfbericht (Qualitätsmanagement)"
doc.confidence = 1.0
doc.classification_status = "dev_reviewed"
doc.reviewed_at = datetime.now()
doc.dev_notes = "Neue Dokumentklasse für QM-Modul"

# 3. System-Update (für alle Praxen!)
broadcast_system_update({
    "type": "new_category",
    "category": "Prüfbericht (Qualitätsmanagement)",
    "pattern": ["Prüfbericht", "Qualitätsmanagement", "QM"]
})
```

### 4b. Decision: Regel hinzufügen

**Developer wählt: "Regel hinzufügen"**
```
Beispiel: OCR erkennt "Rechnung" falsch als "Rechnurig"

Developer erstellt Regel:
"Rechnurig" → "Rechnung" (Typo-Correction)

→ Alle zukünftigen Dokumente mit diesem Typo
   werden automatisch korrigiert!
```

### 4c. Decision: OCR-Problem

**Developer wählt: "OCR-Problem"**
```
Dokument-Qualität zu schlecht:
- Unleserlich
- Verwischt
- Schlechte Auflösung

→ Markiert als "ocr_problem"
→ Notification an User:
   "Bitte bessere Kopie scannen"
```

### 4d. Decision: Training nötig

**Developer wählt: "Training nötig"**
```
Dokument ist schwierig aber lehrreich:
→ Als Training-Daten markieren
→ Für zukünftiges Model-Training nutzen
```

---

## 📊 QUEUE MANAGEMENT

### Priority
```
1. User escalated (höchste Priorität)
   → Echte Unsicherheit von Praxis-Team

2. System escalated (Fehler)
   → OCR-Probleme, Crashes

3. Low confidence (< 40%)
   → System ist sehr unsicher
```

### SLA (Service Level Agreement)
```
Target Response Time:
- Critical (User escalated): 24h
- High (System errors): 48h
- Normal (Low confidence): 1 Woche
```

### Stats
```
GET /api/dev-queue/stats

{
  "total_in_queue": 15,
  "total_reviewed": 142,
  "total_ocr_problems": 8,
  "oldest_item": {
    "id": 234,
    "filename": "unbekannt.pdf",
    "escalated_at": "2026-03-25T10:30:00",
    "days_waiting": 3
  },
  "avg_review_time_hours": 6.2
}
```

---

## 🎓 DEVELOPER TRAINING

### Onboarding (für neue Devs)
```
1. Review 10 Beispiel-Dokumente
   → Verstehe Prozess

2. Erstelle 3 neue Kategorien
   → Übe Category Creation

3. Reviewe echte Queue
   → Supervised by Senior Dev
```

### Best Practices
```
✅ Immer ausführliche Erklärung schreiben
   → Andere Devs verstehen Entscheidung

✅ Pattern dokumentieren
   → Keywords, typische Merkmale

✅ Developer Notes nutzen
   → Intern festhalten warum diese Entscheidung

✅ User-freundliche Kategorie-Namen
   → "Prüfbericht (QM)" nicht "qm_audit_report_v2"
```

---

## 🚀 SYSTEM-UPDATES

### Update-Propagation
```
Developer erstellt neue Kategorie:
"Prüfbericht (Qualitätsmanagement)"

→ System-Update wird generiert
→ Alle VERA-Installationen erhalten Update
→ Alle Praxen profitieren!
```

### Update-Package
```json
{
  "version": "1.1.1",
  "changes": [
    {
      "type": "new_category",
      "category": "Prüfbericht (Qualitätsmanagement)",
      "keywords": ["Prüfbericht", "QM", "Qualitätsmanagement"],
      "pattern": "Prüfbericht.*Qualitäts",
      "created_by_dev": true,
      "created_at": "2026-03-28T16:45:00"
    }
  ]
}
```

### Notification (an User)
```
📢 VERA Update verfügbar!

Neue Features:
• Neue Dokument-Kategorie: "Prüfbericht (QM)"
• Verbesserte OCR-Erkennung
• Bug-Fixes

[Jetzt installieren]
```

---

## 💡 REAL-WORLD SZENARIEN

### Szenario 1: Unbekannter Dokumenttyp
```
Boris: "Was ist das?"
VERA: "Keine Ahnung"
Boris: [Ich bin auch unsicher]

→ Queue (Position 3)
→ Developer reviewt (4h später)
→ Neue Kategorie: "Zertifikat (Fortbildung)"
→ System-Update → Alle Praxen
→ Beim nächsten Fortbildungszertifikat: Auto-klassifiziert!
```

### Szenario 2: OCR-Problem
```
Dokument ist unleserlich (Kopie von Kopie von Fax)

VERA: Confidence 0.12 → Auto-Escalation
→ Queue

Developer: "OCR-Problem - Dokument unleserlich"
→ Markiert als "ocr_problem"
→ Notification an Boris:
   "Dokument-Qualität zu schlecht. 
    Bitte bessere Kopie scannen oder Original fotografieren."
```

### Szenario 3: Systematisches Problem
```
10 Dokumente aus gleicher Quelle:
"Labor XYZ" wird immer falsch klassifiziert

Developer erkennt Pattern:
→ Erstellt Regel: "Labor XYZ" → "Rechnung (Labor)"
→ System-Update
→ Problem behoben für alle zukünftigen Dokumente
```

---

## 📈 SUCCESS METRICS

### Ziele
```
✅ Escalation Rate: < 5% aller Dokumente
✅ Avg Review Time: < 12h
✅ Resolution Rate: > 95%
✅ Reoccurrence Rate: < 2% (gleiches Problem nochmal)
```

### Tracking
```
Wöchentlicher Report:
─────────────────────────────────────
Week 14 (2026-03-24 - 2026-03-30)

Total Documents: 234
Escalated: 11 (4.7%)
Reviewed: 11 (100%)
Avg Review Time: 8.3h

Resolutions:
• New Categories: 3
• Rules Added: 2
• OCR Problems: 4
• Training Data: 2

System Updates: 1
```

---

## 🛠️ TECHNICAL IMPLEMENTATION

### API Endpoints
```
GET  /api/dev-queue/queue
→ Liste aller Dokumente in Queue

POST /api/dev-queue/review
→ Developer reviewt Dokument

GET  /api/dev-queue/stats
→ Queue-Statistiken

DELETE /api/dev-queue/{doc_id}
→ Dokument aus Queue entfernen (skip)
```

### Database
```sql
-- Document statuses for escalation
classification_status:
  - "needs_dev_review"   -- In Queue
  - "dev_reviewed"       -- Reviewt
  - "dev_skipped"        -- Übersprungen
  - "ocr_problem"        -- OCR-Problem
  - "training_data"      -- Für Training

-- Escalation tracking
escalated_at       DATETIME
escalated_by       VARCHAR(128)
user_comment       TEXT
reviewed_at        DATETIME
dev_notes          TEXT
```

---

## 💡 ZUSAMMENFASSUNG

**Boris' Requirement:**
> "Wenn VERA gar nicht weiterkommt, 
>  muss VERA das Entwickler-Team fragen"

**Lösung: Developer Queue**
- ✅ User kann escalieren ("Ich bin auch unsicher")
- ✅ System kann auto-escalieren (OCR-Fehler, sehr low confidence)
- ✅ Developer reviewt systematisch
- ✅ Neue Kategorien/Regeln werden erstellt
- ✅ System-Updates → Alle Praxen profitieren
- ✅ Kontinuierliche Verbesserung!

**Flow:**
```
User unsicher → Escalation → Developer Queue
→ Review → Decision → System Update
→ Alle Praxen profitieren → Problem gelöst!
```

**Resultat:**
- Probleme werden systematisch gelöst
- VERA wird immer schlauer
- User bekommt immer besseren Service
- WIN-WIN-WIN! 🎉

---

**Status:** ✅ IMPLEMENTIERT  
**Autor:** Javix (Sub-Agent)  
**Inspired by:** Boris Reimers - "VERA muss Team fragen können"
