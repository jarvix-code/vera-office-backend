"""
Direct KIQM Import - Standalone script.
"""
import sys
sys.path.insert(0, 'C:/Jarvix/vera-office')

import sqlite3
from pathlib import Path
from datetime import datetime
from backend.db.database import SessionLocal
from backend.models.qm import QMDocument

# Paths
KIQM_DB = Path("C:/Jarvix/QM/data/qmki.db")

# Area mapping
AREA_MAP = {
    "as": "Arbeitssicherheit",
    "qm": "Qualitätsmanagement", 
    "hb": "Handbuch"
}

def import_kiqm():
    """Import all KIQM templates into VERA QM."""
    
    print(f"📂 Connecting to KIQM DB: {KIQM_DB}")
    kiqm_conn = sqlite3.connect(KIQM_DB)
    kiqm_cur = kiqm_conn.cursor()
    
    kiqm_cur.execute("SELECT id, title, area, chapter, file_path, version FROM document_templates")
    templates = kiqm_cur.fetchall()
    
    print(f"📄 Found {len(templates)} KIQM templates")
    
    db = SessionLocal()
    imported = 0
    errors = 0
    
    for idx, row in enumerate(templates):
        doc_id, title, area, chapter, file_path, version = row
        
        try:
            main_area = AREA_MAP.get(area, "Handbuch")
            
            doc = QMDocument(
                title=title,
                main_area=main_area,
                content=f"Importiert aus KIQM: {file_path or 'N/A'}",
                status="Freigegeben",
                current_version=version or "1.0",
                created_at=datetime.now()
            )
            
            db.add(doc)
            db.commit()
            
            imported += 1
            
            if imported % 500 == 0:
                print(f"  ✅ {imported}/{len(templates)}...")
                
        except Exception as e:
            errors += 1
            db.rollback()
            if errors < 10:  # Only print first 10 errors
                print(f"  ❌ {title}: {e}")
    
    db.close()
    kiqm_conn.close()
    
    print(f"\n✅ KIQM Import complete!")
    print(f"  Imported: {imported}")
    print(f"  Errors: {errors}")
    print(f"  Total: {len(templates)}")

if __name__ == "__main__":
    import_kiqm()
