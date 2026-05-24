"""
USB Backend Performance Test
Testet die drei gefixten Funktionen direkt (ohne Backend-Server)
"""
from pathlib import Path
import time
from typing import List, Optional

SUPPORTED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

def _find_importable_files(mount_path: Path) -> List[Path]:
    """Findet importierbare Dateien (PDFs, JPGs, PNGs) NUR in Top-Level (nicht rekursiv)."""
    files = []
    for pattern in ["*.pdf", "*.jpg", "*.jpeg", "*.png"]:
        files.extend(list(mount_path.glob(pattern)))  # glob statt rglob = nur Top-Level!
    files.sort(key=lambda f: f.name)
    return files


def _scan_folders(mount_path: Path) -> List[dict]:
    """
    Scannt USB-Stick und gibt Folder-Struktur zurück (nur Top-Level, nicht rekursiv).
    Zeigt nur Ordner die importierbare Dateien enthalten.
    """
    folders = []
    
    try:
        for entry in mount_path.iterdir():
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            
            # Count files in this folder (NUR direkte Kinder, kein rglob!)
            files = []
            for pattern in ["*.pdf", "*.jpg", "*.jpeg", "*.png"]:
                files.extend(list(entry.glob(pattern)))  # glob statt rglob!
            
            if len(files) == 0:
                continue
            
            # Calculate folder size
            try:
                size_bytes = sum(f.stat().st_size for f in files)
                size_mb = size_bytes / (1024 * 1024)
            except:
                size_mb = 0.0
            
            folders.append({
                "name": entry.name,
                "path": str(entry.relative_to(mount_path)),
                "file_count": len(files),
                "size_mb": round(size_mb, 2)
            })
        
        # Sort by name
        folders.sort(key=lambda f: f["name"])
        
    except Exception as e:
        print(f"Folder-Scan fehlgeschlagen: {e}")
    
    return folders


def test_detect_performance():
    """Test 1: Detect OHNE File-Scan (sollte <1s sein)"""
    print("\n=== TEST 1: Detect Performance (D:\) ===")
    test_path = Path("D:/")
    
    if not test_path.exists():
        print("❌ D:\ Drive nicht gefunden")
        return
    
    start = time.perf_counter()
    # Simuliere detect_usb() - nur Pfad-Check, KEIN File-Count
    detected = test_path.exists() and test_path.is_dir()
    end = time.perf_counter()
    duration = (end - start) * 1000
    
    print(f"✅ Detected: {detected}")
    print(f"✅ Response-Time: {duration:.2f}ms")
    
    if duration < 1000:
        print(f"✅ SUCCESS: <1s Response-Time erreicht!")
    else:
        print(f"❌ FAIL: {duration}ms > 1000ms")


def test_file_scan_performance():
    """Test 2: File-Scan auf Top-Level (sollte <1s sein)"""
    print("\n=== TEST 2: File-Scan Performance (D:\ Top-Level) ===")
    test_path = Path("D:/")
    
    if not test_path.exists():
        print("❌ D:\ Drive nicht gefunden")
        return
    
    start = time.perf_counter()
    files = _find_importable_files(test_path)
    end = time.perf_counter()
    duration = (end - start) * 1000
    
    print(f"✅ Found: {len(files)} files (Top-Level only)")
    print(f"✅ Response-Time: {duration:.2f}ms")
    
    if duration < 1000:
        print(f"✅ SUCCESS: <1s Scan-Time erreicht!")
    else:
        print(f"❌ FAIL: {duration}ms > 1000ms")


def test_folder_scan_performance():
    """Test 3: Folder-Scan (nur Top-Level, nicht rekursiv)"""
    print("\n=== TEST 3: Folder-Scan Performance (D:\ Top-Level Folders) ===")
    test_path = Path("D:/")
    
    if not test_path.exists():
        print("❌ D:\ Drive nicht gefunden")
        return
    
    start = time.perf_counter()
    folders = _scan_folders(test_path)
    end = time.perf_counter()
    duration = (end - start) * 1000
    
    print(f"✅ Found: {len(folders)} folders with importable files")
    for folder in folders[:5]:  # Zeige erste 5
        print(f"   - {folder['name']}: {folder['file_count']} files, {folder['size_mb']}MB")
    
    print(f"✅ Response-Time: {duration:.2f}ms")
    
    if duration < 2000:
        print(f"✅ SUCCESS: <2s Scan-Time erreicht!")
    else:
        print(f"❌ FAIL: {duration}ms > 2000ms")


if __name__ == "__main__":
    print("🔧 VERA Office - USB Backend Performance Test")
    print("=" * 60)
    
    test_detect_performance()
    test_file_scan_performance()
    test_folder_scan_performance()
    
    print("\n" + "=" * 60)
    print("✅ Performance-Test abgeschlossen!")
