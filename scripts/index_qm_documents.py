"""
Index alle QM-Dokumente in VERA Brain
"""
import sys
sys.path.insert(0, 'C:/Jarvix/vera-office')

from backend.core.vera_brain import vera_brain
from backend.db.database import SessionLocal
from backend.models.qm import QMDocument
from loguru import logger

def index_all_qm():
    """Index alle QM-Dokumente."""
    db = SessionLocal()
    
    try:
        # Hole alle QM-Dokumente
        qm_docs = db.query(QMDocument).all()
        
        logger.info(f"📚 Indexiere {len(qm_docs)} QM-Dokumente...")
        
        indexed = 0
        skipped = 0
        
        for doc in qm_docs:
            # Skip if no content
            if not doc.content and not doc.ocr_text:
                skipped += 1
                continue
            
            # Use ocr_text if available, else content
            text = doc.ocr_text or doc.content or ""
            
            # Index in VERA Brain
            vera_brain.index_document(
                doc_type="qm",
                doc_id=doc.id,
                title=doc.title,
                ocr_text=text
            )
            
            indexed += 1
            
            if indexed % 100 == 0:
                logger.info(f"  ✅ {indexed}/{len(qm_docs)} indexiert...")
        
        logger.success(f"✅ Indexierung abgeschlossen!")
        logger.info(f"  Indexiert: {indexed}")
        logger.info(f"  Übersprungen: {skipped}")
        
        # Show stats
        import sqlite3
        conn = sqlite3.connect(vera_brain.db_path)
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM document_index WHERE doc_type='qm'")
        qm_count = cur.fetchone()[0]
        
        logger.info(f"  Total in Brain: {qm_count} QM-Dokumente")
        
        conn.close()
        
    finally:
        db.close()

if __name__ == "__main__":
    index_all_qm()
