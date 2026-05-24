"""
OCR für QM-Dokumente - extrahiert Text aus PDFs
"""
import sys
sys.path.insert(0, 'C:/Jarvix/vera-office')

from pathlib import Path
from backend.db.database import SessionLocal
from backend.models.qm import QMDocument
from backend.core.ocr_engine import OCREngine
from loguru import logger
import time

def extract_ocr():
    """Extract OCR text from QM PDFs."""
    db = SessionLocal()
    ocr = OCREngine()
    
    try:
        # Get all QM docs without OCR text
        docs = db.query(QMDocument).filter(
            QMDocument.ocr_text.is_(None) | (QMDocument.ocr_text == "")
        ).all()
        
        logger.info(f"📄 {len(docs)} QM-Dokumente brauchen OCR...")
        
        processed = 0
        skipped = 0
        errors = 0
        
        for doc in docs:
            # Get file path from content (stored as "KIQM-Datei: <path>")
            if not doc.content or not doc.content.startswith("KIQM-Datei:"):
                skipped += 1
                continue
            
            # Extract path
            file_path_str = doc.content.split("\n")[0].replace("KIQM-Datei: ", "").strip()
            file_path = Path(file_path_str)
            
            # Check if file exists
            if not file_path.exists():
                logger.warning(f"  ⚠️ File not found: {file_path}")
                skipped += 1
                continue
            
            # Only process PDFs
            if file_path.suffix.lower() != ".pdf":
                skipped += 1
                continue
            
            try:
                # Run OCR
                logger.debug(f"  🔍 OCR: {doc.title}")
                start = time.time()
                ocr_text = ocr.extract_text_from_pdf(file_path)
                duration = int((time.time() - start) * 1000)
                
                if ocr_text and len(ocr_text.strip()) > 10:
                    # Update document
                    doc.file_path = str(file_path)
                    doc.ocr_text = ocr_text[:50000]  # Max 50K
                    db.commit()
                    
                    processed += 1
                    
                    if processed % 10 == 0:
                        logger.info(f"  ✅ {processed}/{len(docs)} verarbeitet... ({duration}ms)")
                else:
                    logger.warning(f"  ⚠️ No OCR text: {doc.title}")
                    errors += 1
                    
            except Exception as e:
                logger.error(f"  ❌ OCR failed for {doc.title}: {e}")
                errors += 1
        
        logger.success(f"✅ OCR abgeschlossen!")
        logger.info(f"  Verarbeitet: {processed}")
        logger.info(f"  Übersprungen: {skipped}")
        logger.info(f"  Fehler: {errors}")
        
    finally:
        db.close()

if __name__ == "__main__":
    extract_ocr()
