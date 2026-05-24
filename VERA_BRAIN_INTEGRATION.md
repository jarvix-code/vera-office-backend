# VERA Brain → Backend Integration Guide

**Status:** ✅ READY  
**Backend Port:** 8080  
**Auth Required:** NO (Public Endpoints)

---

## 🚀 Quick Start

### 1. Backend starten

```powershell
cd C:\Jarvix\vera-office
$env:PYTHONIOENCODING="utf-8"
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
```

**Erwarteter Output:**
```
SUCCESS  | VERA Office Backend bereit auf 0.0.0.0:8080
```

### 2. Health Check

```python
import requests
r = requests.get("http://localhost:8080/health")
print(r.json())  # {"status": "healthy", "version": "1.0.0-alpha"}
```

---

## 📋 OCR API Endpoints

### GET /api/qm/ocr/status

**Beschreibung:** OCR-Batch-Status abfragen

**Request:**
```bash
GET http://localhost:8080/api/qm/ocr/status
```

**Response:**
```json
{
  "total": 0,
  "processed": 0,
  "skipped": 0,
  "errors": 0,
  "current": null
}
```

### POST /api/qm/ocr

**Beschreibung:** OCR für QM-Dokumente triggern

#### Variante 1: Einzelnes Dokument (Synchron)

```python
import requests

response = requests.post("http://localhost:8080/api/qm/ocr", json={
    "document_id": 123
})

print(response.json())
# {"status": "success", "document_id": 123}
```

#### Variante 2: Alle Dokumente (Background Task)

```python
import requests

response = requests.post("http://localhost:8080/api/qm/ocr", json={
    "process_all": True
})

print(response.json())
# {"status": "started", "message": "OCR batch processing started"}

# Status pollen:
import time
while True:
    status = requests.get("http://localhost:8080/api/qm/ocr/status").json()
    print(f"Progress: {status['processed']}/{status['total']}")
    
    if status['current'] is None:
        break  # Fertig
    
    time.sleep(2)
```

---

## 🔒 Auth (NICHT erforderlich!)

Die OCR-Endpoints sind **öffentlich** (kein JWT Token erforderlich).

Das bedeutet:
- ❌ Kein `Authorization: Bearer <token>` Header
- ✅ Direkter Zugriff möglich
- ✅ VERA Brain kann ohne Login zugreifen

**Warum?** VERA Brain ist ein interner Dienst, der nicht über das Frontend läuft.

---

## 📊 QM Document Model

### Felder (relevant für OCR):

```python
class QMDocument:
    id: int
    title: str
    file_path: str | None  # PDF-Pfad
    ocr_text: str | None   # OCR-Text (max 50K chars)
    content: str | None    # Legacy: "KIQM-Datei: /path/to/file.pdf"
```

**OCR-Workflow:**
1. Backend findet Dokumente OHNE `ocr_text`
2. Extrahiert Text aus PDF (`file_path` oder `content`)
3. Speichert Text in `ocr_text` (max 50K)
4. Indexiert in VERA Brain (optional)

---

## 🧪 Test-Workflow

### 1. QM-Dokument ohne OCR finden

```python
import sqlite3

db = sqlite3.connect("C:/Jarvix/vera-office/data/vera.db")
cursor = db.cursor()

# Finde Dokumente ohne OCR
cursor.execute("""
    SELECT id, title, file_path 
    FROM qm_documents 
    WHERE ocr_text IS NULL OR ocr_text = ''
""")

docs = cursor.fetchall()
print(f"Dokumente ohne OCR: {len(docs)}")

for doc_id, title, file_path in docs[:5]:
    print(f"  ID {doc_id}: {title}")
```

### 2. OCR für ein Dokument triggern

```python
import requests

doc_id = 1  # Erste ID aus Query oben

response = requests.post("http://localhost:8080/api/qm/ocr", json={
    "document_id": doc_id
})

print(response.json())
```

### 3. Ergebnis prüfen

```python
import sqlite3

db = sqlite3.connect("C:/Jarvix/vera-office/data/vera.db")
cursor = db.cursor()

cursor.execute("SELECT ocr_text FROM qm_documents WHERE id = ?", (doc_id,))
ocr_text = cursor.fetchone()[0]

print(f"OCR-Text Length: {len(ocr_text) if ocr_text else 0}")
print(f"Preview: {ocr_text[:200] if ocr_text else 'KEIN TEXT'}")
```

---

## ⚠️ Wichtige Hinweise

### Encoding
- Backend läuft mit `PYTHONIOENCODING=utf-8`
- Alle Logs sind jetzt ASCII-kompatibel (keine Emojis)
- Keine UnicodeEncodeError mehr

### Performance
- OCR ist **langsam** (1-5 Sekunden pro PDF)
- Bei `process_all=True` → Background Task verwenden
- Status-Endpoint für Progress-Tracking nutzen

### Fehlerbehandlung
- PDF nicht gefunden → `skipped += 1`
- OCR failed → `errors += 1`
- Kein Text extrahiert → `errors += 1`

---

## 🎯 Next Steps für VERA Brain

### Integration Checklist:

- [ ] Backend-URL konfigurieren (`http://localhost:8080`)
- [ ] OCR-Status-Endpoint testen
- [ ] Single-Document OCR testen
- [ ] Batch-OCR implementieren (mit Progress)
- [ ] Error-Handling für Failed OCR
- [ ] OCR-Text in VERA Brain indexieren

### Code-Beispiel (VERA Brain):

```python
class VERABackendClient:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
    
    def ocr_document(self, doc_id: int):
        """OCR für einzelnes Dokument."""
        r = requests.post(f"{self.base_url}/api/qm/ocr", json={
            "document_id": doc_id
        })
        return r.json()
    
    def ocr_all(self):
        """OCR für alle Dokumente (Background)."""
        r = requests.post(f"{self.base_url}/api/qm/ocr", json={
            "process_all": True
        })
        return r.json()
    
    def ocr_status(self):
        """OCR-Status abfragen."""
        r = requests.get(f"{self.base_url}/api/qm/ocr/status")
        return r.json()

# Usage:
client = VERABackendClient()
client.ocr_all()

# Poll:
import time
while True:
    status = client.ocr_status()
    print(f"{status['processed']}/{status['total']}")
    if status['current'] is None:
        break
    time.sleep(2)
```

---

## ✅ Ready to Go!

Backend ist stabil, OCR-API funktioniert, keine Auth erforderlich.  
VERA Brain kann jetzt QM-Dokumente mit OCR verarbeiten!

---

_Guide erstellt: 2026-03-26_  
_Backend Version: 1.0.0-alpha_
