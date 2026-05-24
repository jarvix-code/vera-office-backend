"""
VERA Office - Pipeline Test
Testet die neue PDF + OCR Pipeline mit echten Dateien aus der Inbox
"""
import asyncio
import sys
from pathlib import Path

# PYTHONPATH Setup
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import config
from backend.core.document_processor import DocumentProcessor
from backend.db.database import init_db
from loguru import logger

async def test_single_file():
    """
    Testet die Pipeline mit einer einzigen Datei aus der Inbox
    """
    # Init DB
    init_db()
    
    # Hole erste Datei aus Inbox
    inbox = config.INBOX_DIR
    files = list(inbox.glob("*.pdf"))[:1]  # Erste PDF
    
    if not files:
        logger.error("Keine Dateien in Inbox gefunden!")
        return
    
    test_file = files[0]
    logger.info(f"[TEST] Verarbeite Test-Datei: {test_file.name}")
    
    # Verarbeite
    processor = DocumentProcessor()
    doc = await processor.process_document(test_file)
    
    if doc:
        logger.success(f"[SUCCESS] Dokument verarbeitet!")
        logger.info(f"  ID: {doc.id}")
        logger.info(f"  Filename: {doc.filename}")
        logger.info(f"  OCR-Text: {len(doc.ocr_text or '')} Zeichen")
        logger.info(f"  Pages: {doc.page_count}")
    else:
        logger.error("[FAILED] Verarbeitung fehlgeschlagen")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("VERA Pipeline Test - PDF + OCR + DB Integration")
    logger.info("=" * 60)
    
    asyncio.run(test_single_file())
