# VERA Verification System v2.0

**Update:** 2026-03-28  
**Grund:** Boris' Feedback - Active Learning + Unbegrenzte Kategorien

---

## 📋 ÜBERSICHT

**Problem (v1.0):**
- ❌ "UNBEKANNT" bei Unsicherheit → User muss blind raten
- ❌ Vordefinierte Kategorien → schränkt System ein
- ❌ Keine User-Interaktion → schlechtes Learning

**Lösung (v2.0):**
- ✅ Active Learning Dialog → VERA fragt User persönlich
- ✅ Unbegrenzte Kategorien → User erstellt neue Kategorien dynamisch
- ✅ Dokument-Ansicht integriert → User hat Kontext
- ✅ Escalation System → Developer-Queue wenn User + VERA unsicher

---

## 🔄 BORIS' FEEDBACK

### Feedback 1 (18:01): "Warum fragt VERA nicht den User?"

**Problem:**
```python
if confidence < 0.85:
    return "UNBEKANNT - BITTE PRÜFEN"
```

**Lösung:**
```python
if confidence < 0.85:
    return active_learning_dialog(
        question="Hey {user}, was ist das?",
        show_document_button=True,
        free_text_field=True
    )
```

### Feedback 2 (18:06): "Kategorien sind UNBEGRENZT!"

**Problem:**
```vue
<q-select 
  :options="['checkliste', 'arbeitsanweisung', 'sonstige']"
/>
```

**Lösung:**
```vue
<q-input
  type="textarea"
  label="Was ist das für ein Dokument?"
  hint="Erkläre ausführlich - VERA lernt daraus!"
  rows="5"
/>
<!-- KEINE Dropdowns! User schreibt FREI! -->
```

---

## 🎯 COMPLETE WORKFLOW

### 1. Dokument wird verarbeitet
```
✓ Scan
✓ OCR
✓ Text extrahiert
```

### 2. VERA klassifiziert
```python
result = safe_classifier.classify_with_active_learning(
    text=ocr_text,
    user_name="Boris"
)

if result["status"] == "confident":
    # Confidence >= 85% → Auto-File
    auto_classify(category)
else:
    # Confidence < 85% → Active Learning
    ask_user(result["frage"])
```

### 3a. HIGH Confidence (>= 85%)
```
→ Auto-klassifiziert
→ Dokument abgelegt
→ User sieht Benachrichtigung
```

### 3b. LOW Confidence (< 85%)
```
→ VERA fragt: "Hey Boris, was ist das?"
→ Notification erscheint
→ User klickt "Jetzt helfen"
```

### 4. Active Learning Dialog öffnet
```
╔══════════════════════════════════════════╗
║  🤔 VERA braucht Hilfe!                  ║
║                                          ║
║  Hey Boris, ich kann das Dokument       ║
║  nicht zuordnen. Was ist das?           ║
║                                          ║
║  [📄 Dokument ansehen]                  ║
║  [Jetzt helfen]  [Später]               ║
╚══════════════════════════════════════════╝
```

### 5. User klickt "Dokument ansehen"
```
→ Reader-View (Vollbild)
→ PDF anschauen
→ Zoom, Navigation
→ [✓ Fertig - VERA erklären]
```

### 6. Erklärungsformular
```
╔══════════════════════════════════════════╗
║  Was ist das für ein Dokument?           ║
║                                          ║
║  ┌────────────────────────────────────┐ ║
║  │ [Freies Textfeld]                  │ ║
║  │                                    │ ║
║  │ User schreibt:                     │ ║
║  │ "Das ist ein Wartungsvertrag für   │ ║
║  │  unsere Röntgengeräte von SiroDent"│ ║
║  └────────────────────────────────────┘ ║
║                                          ║
║  [Speichern & VERA lernt]               ║
║  [Ich bin auch unsicher]                ║
╚══════════════════════════════════════════╝
```

### 7a. User erklärt → VERA lernt
```python
# Extract category from explanation
category_info = extract_category_from_explanation(
    "Das ist ein Wartungsvertrag für Röntgengeräte"
)
# → {"main": "Wartungsvertrag", "sub": "Medizingeräte"}

# Add to dynamic categories
add_new_category(category_info, user_id, user_name)

# Update document
doc.category = "Wartungsvertrag (Medizingeräte)"
doc.confidence = 1.0  # User-confirmed!
doc.classification_status = "user_confirmed"
```

### 7b. User unsicher → Escalation
```python
# User klickt "Ich bin auch unsicher"
doc.classification_status = "needs_dev_review"
doc.escalated_at = now()
doc.escalated_by = user_name

# Developer Queue
add_to_developer_queue(doc)
```

### 8. VERA bestätigt
```
✅ Danke, Boris!

Ich habe gelernt:
• Wartungsvertrag (Medizingeräte)
• SiroDent = Lieferant
• Röntgengeräte = Medizingeräte

Beim nächsten ähnlichen Dokument
bin ich sicherer! 📈
```

---

## 🧠 DYNAMIC CATEGORIES

### Konzept
**Kategorien werden NICHT vordefiniert!**

User definiert Kategorien durch freie Erklärungen:
```
User: "Das ist ein Wartungsvertrag für Röntgengeräte"
→ VERA extrahiert: "Wartungsvertrag (Medizingeräte)"
→ Neue Kategorie wird erstellt
→ Beim nächsten Mal: Auto-Erkennung!
```

### Wachstum
```
Woche 1:  5 Dokumente → 3 Kategorien
Woche 2: 20 Dokumente → 8 Kategorien (12 auto-klassifiziert!)
Monat 3: 500 Dokumente → 40 Kategorien (85% auto-klassifiziert!)
Jahr 1: 5000 Dokumente → 150+ Kategorien (95% auto-klassifiziert!)
```

### Beispiel-Kategorien
```
- Wartungsvertrag (Medizingeräte)
- Wartungsvertrag (Praxismöbel)
- Rechnung (Labor)
- Rechnung (Software)
- Behördenpost (Gesundheitsamt)
- Arbeitsvertrag
- Gehaltsabrechnung
- Mietvertrag (Praxisräume)
- Versicherungspolice (Haftpflicht)
- ... UNBEGRENZT!
```

---

## ⚠️ ESCALATION SYSTEM

### Wann?
- User ist auch unsicher ("Ich bin auch unsicher" Button)
- VERA kann gar nicht klassifizieren (Fehler, schlechte OCR)

### Developer Queue
```
📋 Entwickler-Review Queue (15)

┌─────────────────────────────────────────┐
│ 📄 unbekanntes_dokument.pdf             │
│    User: "Ich bin auch unsicher"        │
│    Confidence: 0.42                     │
│    [Review]                             │
├─────────────────────────────────────────┤
│ 📄 schlechte_qualitaet.pdf              │
│    OCR: Schlecht lesbar                 │
│    [Review]                             │
└─────────────────────────────────────────┘
```

### Developer Actions
1. **Neue Kategorie erstellen** → System-Update → Alle Praxen profitieren
2. **Regel hinzufügen** → Klassifikations-Regel
3. **OCR-Problem** → Qualitätsproblem markieren
4. **Training nötig** → Als Training-Daten markieren

---

## 📊 SUCCESS METRICS

### Ziele (nach 3 Monaten)
- ✅ Auto-Classification Rate: >= 85%
- ✅ User Help Request Rate: <= 15%
- ✅ Escalation Rate: <= 5%
- ✅ Category Growth: 5-10 neue/Woche
- ✅ User Satisfaction: "VERA lernt wirklich!"

### Tracking
```
GET /api/active-learning/stats

{
  "total_documents": 500,
  "auto_classified": 425,      // 85%
  "user_confirmed": 60,         // 12%
  "needs_user_help": 10,        // 2%
  "needs_dev_review": 5,        // 1%
  "auto_classification_rate": 85.0,
  "category_stats": {
    "total_categories": 42,
    "most_used": "Rechnung (Labor)",
    "avg_docs_per_category": 11.9
  }
}
```

---

## 🚀 IMPLEMENTATION

### Backend
- ✅ `dynamic_categories.py` - Unbegrenzte Kategorien
- ✅ `safe_classifier.py` - Active Learning statt "UNBEKANNT"
- ✅ `active_learning.py` - API Endpoints
- ✅ `developer_queue.py` - Dev-Review Queue

### Frontend
- ✅ `ActiveLearningDialog.vue` - User-Dialog
- ✅ `DocumentReaderModal.vue` - Vollbild PDF-Viewer
- ✅ `UnclearDocumentsView.vue` - Queue-Übersicht

### Database
- ✅ Document Model erweitert:
  - `classification_status` (pending, auto_classified, user_confirmed, needs_user_help, needs_dev_review, ...)
  - `user_explanation` (freie User-Erklärung)
  - `user_comment` (Escalation-Kommentar)
  - `escalated_at`, `escalated_by`, `reviewed_at`, `dev_notes`

---

## 💡 WARUM IST DAS BESSER?

### vs. "UNBEKANNT - BITTE PRÜFEN"
- ❌ User lost ohne Kontext
- ❌ Kein Dokument-Zugang
- ❌ Keine Guidance
- ❌ Minimales Learning

### Active Learning (v2.0)
- ✅ User kann Dokument sehen (Kontext!)
- ✅ Persönliche Ansprache ("Hey Boris")
- ✅ Ausführliche Erklärung möglich
- ✅ Rich Learning (Keywords, Context, Patterns)
- ✅ Kategorien wachsen organisch
- ✅ Feedback-Loop (User sieht Impact)

**→ Maximales Learning bei guter UX!**

---

## 🎓 BEST PRACTICES

1. **Immer Kontext geben** → Dokument-Ansicht integrieren
2. **Freie Erklärung** → KEINE Dropdowns, User schreibt frei
3. **Positives Feedback** → "Danke, ich habe gelernt!"
4. **Progress zeigen** → "Beim nächsten Mal sicherer!"
5. **Escalation ermöglichen** → Wenn User unsicher ist
6. **Developer-Queue** → Systematische Verbesserung

---

**Status:** ✅ IMPLEMENTIERT  
**Version:** 2.0  
**Autor:** Javix (Sub-Agent)  
**Inspired by:** Boris Reimers - UX-Feedback 2026-03-28
