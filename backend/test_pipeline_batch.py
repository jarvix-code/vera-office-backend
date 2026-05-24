"""
VERA Office - Pipeline Batch Test
Verarbeitet ALLE 755 Dateien aus der Inbox
"""
import asyncio
import sys
from pathlib import Path
import time

# PYTHONPATH Setup
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import config
from backend.core.document_processor import DocumentProcessor
from backend.db.database import init_db, SessionLocal
from backend.models.document import Document
from loguru import logger

async def process_all_files():
    """
    Verarbeitet ALLE PDFs aus der Inbox
    """
    # Init DB
    init_db()
    
    # Hole alle PDFs aus Inbox
    inbox = config.INBOX_DIR
    files = list(inbox.glob("*.pdf"))
    
    if not files:
        logger.error("Keine Dateien in Inbox gefunden!")
        return
    
    logger.info(f"[BATCH] Gefunden: {len(files)} PDFs in Inbox")
    logger.info(f"[BATCH] Starte Batch-Verarbeitung...")
    
    processor = DocumentProcessor()
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    start_time = time.time()
    
    for idx, file_path in enumerate(files, 1):
        try:
            logger.info(f"[{idx}/{len(files)}] Verarbeite: {file_path.name}")
            
            doc = await processor.process_document(file_path)
            
            if doc:
                success_count += 1
                logger.success(f"  ✓ Dokument ID {doc.id} ({len(doc.ocr_text or '')} Zeichen)")
            else:
                skip_count += 1
                logger.warning(f"  ⏭ Übersprungen (existiert bereits?)")
        
        except Exception as e:
            error_count += 1
            logger.error(f"  ❌ Fehler: {e}")
        
        # Progress update every 50 files
        if idx % 50 == 0:
            elapsed = time.time() - start_time
            rate = idx / elapsed
            eta = (len(files) - idx) / rate if rate > 0 else 0
            logger.info(f"[PROGRESS] {idx}/{len(files)} ({idx/len(files)*100:.1f}%) | {rate:.1f} files/sec | ETA: {eta/60:.1f} min")
    
    elapsed_total = time.time() - start_time
    
    logger.info("=" * 60)
    logger.info("BATCH PROCESSING ABGESCHLOSSEN")
    logger.info("=" * 60)
    logger.info(f"  Dateien gesamt: {len(files)}")
    logger.info(f"  ✅ Erfolgreich: {success_count}")
    logger.info(f"  ⏭ Übersprungen: {skip_count}")
    logger.info(f"  ❌ Fehler: {error_count}")
    logger.info(f"  ⏱ Zeit: {elapsed_total/60:.1f} Minuten")
    logger.info(f"  📈 Rate: {len(files)/elapsed_total:.1f} files/sec")
    
    # Check DB
    db = SessionLocal()
    doc_count = db.query(Document).count()
    db.close()
    logger.info(f"  💾 Dokumente in DB: {doc_count}")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("VERA Batch Test - 755 Dateien Verarbeitung")
    logger.info("=" * 60)
    
    asyncio.run(process_all_files())
