"""
Sync KIQM documents: Add OCR-Text from KIQM to VERA QM documents.
"""
import sys
sys.path.insert(0, 'C:/Jarvix/vera-office')

import sqlite3
from backend.db.database import SessionLocal
from backend.models.qm import QMDocument

# Paths
KIQM_DB = "C:/Jarvix/QM/data/qmki.db"
VERA_DB = "C:/Jarvix/vera-office/data/vera.db"

def sync_ocr():
    """Add OCR text from KIQM to VERA QM documents."""
    
    # Connect to KIQM
    kiqm_conn = sqlite3.connect(KIQM_DB)
    kiqm_cur = kiqm_conn.cursor()
    
    # VERA session
    db = SessionLocal()
    
    # Get all KIQM templates with file paths
    kiqm_cur.execute("""
        SELECT title, file_path, meta_data
        FROM document_templates
    """)
    
    kiqm_docs = {}
    for title, file_path, meta_data in kiqm_cur.fetchall():
        if file_path and file_path.endswith('.pdf'):
            kiqm_docs[title] = {
                'file_path': file_path,
                'meta_data': meta_data
            }
    
    print(f"📚 Found {len(kiqm_docs)} KIQM documents with PDFs")
    
    # Update VERA QM documents with file paths
    vera_docs = db.query(QMDocument).all()
    
    updated = 0
    
    for vera_doc in vera_docs:
        if vera_doc.title in kiqm_docs:
            kiqm_data = kiqm_docs[vera_doc.title]
            
            # Update file_path (if not already set)
            if not hasattr(vera_doc, 'file_path') or not vera_doc.file_path:
                # QMDocument doesn't have file_path yet - we need to add it
                # For now: store in content field
                vera_doc.content = f"KIQM-Datei: {kiqm_data['file_path']}\n\n{vera_doc.content}"
                db.commit()
                updated += 1
                
                if updated % 100 == 0:
                    print(f"  ✅ {updated} documents updated...")
    
    print(f"\n✅ Sync complete!")
    print(f"  Updated: {updated}/{len(vera_docs)}")
    
    kiqm_conn.close()
    db.close()

if __name__ == "__main__":
    sync_ocr()
