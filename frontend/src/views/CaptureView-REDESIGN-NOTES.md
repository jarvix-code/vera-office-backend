# VERA Office Capture View - iPad Redesign

## PROBLEM (AKTUELL):
- **File System Access API** = Zugriff auf LOKALE iPad-Dateien
- Realität: iPad ist nur **Remote-Display** für PC-Backend!

## RICHTIGES DESIGN:

### Architektur
```
USB-Stick → PC (192.168.178.44)
              ↓
         Backend /api/import-usb/scan
              ↓
         Frontend (iPad zeigt Dateien an)
              ↓
        User wählt aus
              ↓
         Backend importiert direkt
```

### Backend-APIs (EXISTIEREN BEREITS!):

```python
GET  /api/import-usb/scan
  → Response: {
      "mounted": true,
      "path": "D:\\",
      "file_count": 42,
      "files": ["file1.pdf", "file2.jpg"],
      "folders": [
        {"name": "QM-Dokumente", "path": "QM-Dokumente", "file_count": 12, "size_mb": 5.2}
      ]
    }

POST /api/import-usb
  → Body: {"folders": ["QM-Dokumente"]}  // optional: nur bestimmte Ordner
  → Response: {"job_id": "abc123", "total_files": 12, "message": "..."}

GET  /api/import-usb/progress/{job_id}
  → Response: {"status": "importing", "total": 12, "done": 5, "errors": 0}

GET  /api/import-usb/detect
  → Response: {"detected": true, "mount_path": "D:\\", "file_count": 42}
```

## FRONTEND CHANGES:

### CaptureView.vue - USB Flow

**1. Kamera (BLEIBT GLEICH):**
- iPad nimmt Foto auf
- Upload → Backend `/api/documents/upload`
- Backend macht OCR + Klassifizierung
- iPad zeigt Ergebnis

**2. "Ordner auswählen" → "USB-Stick scannen":**

**ALT (File System Access API - RAUS!):**
```js
// showDirectoryPicker() → iPad-lokale Dateien
const dirHandle = await window.showDirectoryPicker()
```

**NEU (Backend USB API):**
```js
// Scan USB via Backend API
async function scanUSB() {
  const response = await fetch('/api/import-usb/scan')
  const data = await response.json()
  
  if (!data.mounted) {
    Notify.create({ message: 'Kein USB-Stick gefunden' })
    return
  }
  
  // Zeige Folder-Struktur
  usbFolders.value = data.folders
  usbFiles.value = data.files
  showUSBView.value = true
}

// Import selektierter Ordner
async function importSelectedFolders() {
  const selectedFolderNames = selectedFolders.value
  
  const response = await fetch('/api/import-usb', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ folders: selectedFolderNames })
  })
  
  const data = await response.json()
  jobId.value = data.job_id
  
  // Poll Progress
  pollImportProgress(data.job_id)
}

// Progress Polling
async function pollImportProgress(jobId) {
  const interval = setInterval(async () => {
    const response = await fetch(`/api/import-usb/progress/${jobId}`)
    const data = await response.json()
    
    importProgress.value = data
    
    if (data.status === 'done' || data.status === 'error') {
      clearInterval(interval)
      Notify.create({ message: `Import abgeschlossen: ${data.done}/${data.total}` })
      router.push('/documents')
    }
  }, 1000)
}
```

### UI-Flow (iPad):

**Schritt 1 - Card View:**
```
[Kamera]  [USB-Stick scannen]  [Scanner]
```

**Schritt 2 - USB-Scan (Backend):**
```
Button: "USB-Stick scannen"
  ↓
GET /api/import-usb/scan
  ↓
Zeige Folder-Liste:
  ☑ QM-Dokumente (12 Dateien, 5.2 MB)
  ☑ Rechnungen (8 Dateien, 2.1 MB)
  ☐ Fotos (0 Dateien)

Button: "Import starten"
```

**Schritt 3 - Import läuft:**
```
POST /api/import-usb { folders: ["QM-Dokumente", "Rechnungen"] }
  ↓
Progress-Bar: 5/20 Dateien importiert
  ↓
GET /api/import-usb/progress/{job_id} (jede Sekunde)
```

**Schritt 4 - Fertig:**
```
✅ 20 Dateien importiert!
→ Navigate zu /documents
```

## CODE CHANGES:

### Entfernen:
- `showDirectoryPicker()` Logik (Zeile ~450-500)
- `readDirectory()` Funktion
- `folderFiles`, `selectedFiles`, `folderScanning` (lokale States)

### Hinzufügen:
- `scanUSB()` → Backend API call
- `importSelectedFolders()` → POST /api/import-usb
- `pollImportProgress()` → GET /api/import-usb/progress/{job_id}

### States umbenennen:
- `showFolderView` → `showUSBView`
- `folderImporting` → `usbImporting`
- `folderFiles` → `usbFolders` (Folder-Liste vom Backend!)

## BROWSER-KOMPATIBILITÄT:

**ALT:**
- File System Access API → nur Chrome/Edge
- Safari NICHT unterstützt

**NEU:**
- Backend-API → ALLE Browser (Safari, Chrome, Edge, Firefox)
- iPad Safari ✅
- Keine lokalen Dateisystem-Zugriffe nötig!

## TESTING:

1. **USB-Stick am PC einstecken** (z.B. D:\)
2. **iPad Safari:** https://192.168.178.44:8443/capture
3. **Button "USB-Stick scannen"** → Backend listet Dateien
4. **Ordner auswählen** → Import startet
5. **Progress-Bar** → zeigt Fortschritt
6. **Fertig** → Navigate zu /documents

## PRIORITY:
P0 - Grundlegendes Architektur-Problem (File System Access API war falsch!)

## ESTIMATED TIME:
45-60 Min (Frontend-Redesign + Testing)
