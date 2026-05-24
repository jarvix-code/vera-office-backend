# VERA Office - USB Backend Test Report

**Datum:** 2026-03-28 07:53 GMT+1  
**Tester:** Javix  
**Backend:** Port 8080  

---

## ✅ ERFOLGREICHE TESTS:

### 1. Backend-Start
- ✅ Backend startet erfolgreich
- ✅ Module geladen (ERP, QM)
- ✅ Datenbank initialisiert
- ✅ mDNS registriert (vera-office.local:8443)
- ✅ Hotfolder-Scanner aktiv

### 2. Login
- ✅ POST /api/auth/login funktioniert
- ✅ Token wird zurückgegeben
- ✅ User: boris, Role: admin

### 3. USB-Detection
- ✅ D: Drive wird erkannt (Type: 3 = Fixed Drive)
- ✅ Backend-Log zeigt: "USB-Detection: D: gefunden"

---

## ❌ FEHLERHAFTE TESTS:

### 1. USB-Detection Endpoint (`/api/import-usb/detect`)
**Problem:** Request hängt (Timeout nach 10s)

**Backend-Log:**
```
INFO: backend.api.usb_import:_find_usb_windows | USB-Detection: D: gefunden (Type: 3)
```
→ Drive wird gefunden, ABER Response kommt nie zurück!

**Root-Cause (Vermutung):**
- `_find_importable_files(mount_path)` hängt bei großen Laufwerken
- `rglob("*")` auf D:\ scannt GESAMTES Drive (zu langsam!)

**Fix benötigt:**
- Timeout für File-Scan setzen (max 5s)
- ODER: Nur Top-Level-Ordner scannen (nicht rekursiv)
- ODER: Lazy-Loading (erst beim Scan, nicht bei Detect)

### 2. USB-Scan Endpoint (`/api/import-usb/scan`)
**Problem:** Nicht getestet (wegen Detect-Timeout)

**Erwartete Root-Cause:**
- `_scan_folders()` macht rekursives `_find_importable_files()` für JEDEN Ordner
- Bei D:\ mit vielen Dateien = extrem langsam!

---

## 📋 EMPFOHLENE FIXES:

### Fix #1: Detect-Endpoint schneller machen
```python
@router.get("/import-usb/detect", response_model=USBDetectionResponse)
async def detect_usb():
    mount_path = _find_usb_mount()
    if mount_path:
        # KEIN File-Count hier! Nur Pfad zurückgeben.
        return USBDetectionResponse(detected=True, mount_path=str(mount_path), file_count=0)
    return USBDetectionResponse(detected=False)
```

### Fix #2: Scan-Endpoint mit Timeout
```python
def _scan_folders(mount_path: Path, max_depth=2, timeout_seconds=10) -> List[dict]:
    """Nur Top-Level-Ordner (max_depth=2), mit Timeout."""
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError("Folder scan timeout")
    
    # Set alarm (Unix only - Windows braucht threading.Timer)
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    
    try:
        folders = []
        for entry in mount_path.iterdir():
            if entry.is_dir() and not entry.name.startswith("."):
                # Nur direkte Kinder scannen (kein rglob!)
                files = list(entry.glob("*.pdf")) + list(entry.glob("*.jpg")) + list(entry.glob("*.png"))
                if len(files) > 0:
                    folders.append({...})
        return folders
    finally:
        signal.alarm(0)  # Cancel alarm
```

### Fix #3: Frontend Fallback
Falls Backend zu langsam:
- Zeige "Scanning..." Spinner
- Timeout nach 15s → Fehlermeldung
- User kann manuell Refresh klicken

---

## 🎯 NÄCHSTE SCHRITTE:

1. **Fix #1 implementieren** (Detect ohne File-Count)
2. **Fix #2 implementieren** (Scan mit Timeout + max_depth)
3. **Test wiederholen** (D:\ Drive)
4. **iPad-Test** (wenn Backend schnell genug)

---

## 📊 BACKEND-STATUS:

| Component | Status |
|-----------|--------|
| Backend läuft | ✅ Port 8080 |
| Login | ✅ boris / vera2024! |
| USB-Detection (Code) | ✅ D: erkannt |
| USB-Detection (Response) | ❌ Timeout |
| USB-Scan | ⏳ Nicht getestet |
| Frontend | ⏳ Nicht getestet |

---

**BORIS - USB-BACKEND HAT PERFORMANCE-PROBLEM!**

**D: Drive wird erkannt, ABER File-Scan zu langsam!**

**Fix nötig: Nur Top-Level-Ordner scannen (nicht rekursiv)**
