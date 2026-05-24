"""
Manueller Inbox-Processor
Triggert process_new_document() für alle existierenden Inbox-Dateien
"""
import asyncio
from pathlib import Path
from backend.config import config
from backend.main import process_new_document
from loguru import logger

async def process_all_inbox_files():
    """Verarbeitet alle Dateien in Inbox"""
    inbox_path = config.INBOX_DIR
    
    # Finde alle verarbeitbaren Dateien
    allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif'}
    files = [
        f for f in inbox_path.iterdir()
        if f.is_file() and f.suffix.lower() in allowed_extensions
    ]
    
    logger.info(f"[BATCH] Verarbeite {len(files)} Dateien aus Inbox...")
    
    for i, file_path in enumerate(files, 1):
        try:
            logger.info(f"[{i}/{len(files)}] {file_path.name}")
            await process_new_document(file_path)
        except Exception as e:
            logger.error(f"[ERROR] Fehler bei {file_path.name}: {e}")
    
    logger.success(f"[OK] Batch-Verarbeitung abgeschlossen: {len(files)} Dateien")

if __name__ == "__main__":
    asyncio.run(process_all_inbox_files())
