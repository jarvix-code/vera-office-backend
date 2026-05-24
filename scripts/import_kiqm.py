"""
Import KIQM documents into VERA Office QM module.

Maps old KIQM structure to new VERA QM:
- document_templates → qm_documents
- area (as/qm/hb) → main_area (Arbeitssicherheit/Qualitätsmanagement/Handbuch)
- chapter → blzk_chapter (e.g., "01_BeitrO...")
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Paths
KIQM_DB = Path("C:/Jarvix/QM/data/qmki.db")
VERA_DB = Path("C:/Jarvix/vera-office/data/vera.db")

# Area mapping
AREA_MAP = {
    "as": "Arbeitssicherheit",
    "qm": "Qualitätsmanagement", 
    "hb": "Handbuch"
}

def import_documents():
    """Import all KIQM templates as VERA QM documents."""
    
    # Connect to both databases
    kiqm_conn = sqlite3.connect(KIQM_DB)
    vera_conn = sqlite3.connect(VERA_DB)
    
    kiqm_cur = kiqm_conn.cursor()
    vera_cur = vera_conn.cursor()
    
    # Fetch all templates
    kiqm_cur.execute("""
        SELECT id, title, area, chapter, file_path, file_type, version, meta_data
        FROM document_templates
    """)
    
    templates = kiqm_cur.fetchall()
    print(f"Found {len(templates)} KIQM templates")
    
    imported = 0
    skipped = 0
    
    for row in templates:
        doc_id, title, area, chapter, file_path, file_type, version, meta_data = row
        
        # Map area to VERA format
        main_area = AREA_MAP.get(area, "Handbuch")
        
        # Extract chapter ID (e.g., "01_BeitrO..." → "hb_01")
        blzk_chapter = None
        if chapter:
            parts = chapter.split("_")
            if len(parts) >= 1:
                blzk_chapter = f"{area}_{parts[0]}"
        
        # Insert into VERA QM
        try:
            vera_cur.execute("""
                INSERT INTO qm_documents (
                    title, main_area, blzk_chapter, content, 
                    status, current_version, file_path, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                title,
                main_area,
                blzk_chapter,
                f"Importiert aus KIQM: {file_path or 'N/A'}",
                "Freigegeben",  # Assume all KIQM docs are approved
                version or "1.0",
                file_path,
                datetime.now().isoformat()
            ))
            imported += 1
            
            if imported % 100 == 0:
                print(f"  Imported {imported}/{len(templates)}...")
                
        except sqlite3.IntegrityError as e:
            # Duplicate - skip
            skipped += 1
    
    # Commit and close
    vera_conn.commit()
    
    print(f"\n✅ Import complete!")
    print(f"  Imported: {imported}")
    print(f"  Skipped (duplicates): {skipped}")
    print(f"  Total: {len(templates)}")
    
    kiqm_conn.close()
    vera_conn.close()

if __name__ == "__main__":
    if not KIQM_DB.exists():
        print(f"❌ KIQM database not found: {KIQM_DB}")
        sys.exit(1)
    
    if not VERA_DB.exists():
        print(f"❌ VERA database not found: {VERA_DB}")
        sys.exit(1)
    
    print(f"Importing from {KIQM_DB}")
    print(f"           to {VERA_DB}\n")
    
    import_documents()
