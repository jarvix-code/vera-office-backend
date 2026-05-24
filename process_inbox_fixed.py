"""
Manueller Inbox-Processor mit PDF-Support
Konvertiert PDFs zu Bildern und verarbeitet dann alle Files
"""
import asyncio
import fitz  # PyMuPDF
from pathlib import Path
from backend.config import config
from backend.main import process_new_document
from loguru import logger

def pdf_to_image(pdf_path: Path, output_dir: Path) -> Path:
    """Konvertiert erste Seite eines PDFs zu JPG"""
    try:
        doc = fitz.open(str(pdf_path))
        page = doc[0]  # Erste Seite
        
        # Render zu Image (300 DPI)
        mat = fitz.Matrix(300/72, 300/72)  # 72 DPI default → 300 DPI
        pix = page.get_pixmap(matrix=mat)
        
        # Speichere als JPG
        output_path = output_dir / f"{pdf_path.stem}.jpg"
        pix.save(str(output_path))
        
        doc.close()
        logger.debug(f"  PDF→JPG: {pdf_path.name} → {output_path.name}")
        return output_path
    except Exception as e:
        logger.error(f"  PDF-Konvertierung fehlgeschlagen: {pdf_path.name} - {e}")
        return None

async def process_all_inbox_files():
    """Verarbeitet alle Dateien in Inbox (PDFs werden zu JPGs konvertiert)"""
    inbox_path = config.INBOX_DIR
    temp_dir = config.DATA_DIR / "temp"
    temp_dir.mkdir(exist_ok=True)
    
    # Finde alle PDFs
    pdf_files = list(inbox_path.glob("*.pdf"))
    image_files = [
        f for f in inbox_path.iterdir()
        if f.is_file() and f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.tiff', '.tif'}
    ]
    
    total = len(pdf_files) + len(image_files)
    logger.info(f"[BATCH] Verarbeite {total} Dateien aus Inbox ({len(pdf_files)} PDFs, {len(image_files)} Bilder)...")
    
    processed = 0
    errors = 0
    
    # Verarbeite PDFs (konvertiere zu JPG, dann process)
    for i, pdf_path in enumerate(pdf_files, 1):
        try:
            logger.info(f"[{i}/{total}] {pdf_path.name} (PDF→JPG)")
            
            # Konvertiere PDF zu JPG
            jpg_path = pdf_to_image(pdf_path, temp_dir)
            if not jpg_path:
                errors += 1
                continue
            
            # Verarbeite JPG
            await process_new_document(jpg_path)
            
            # Cleanup: Lösche temp JPG
            jpg_path.unlink(missing_ok=True)
            
            processed += 1
        except Exception as e:
            logger.error(f"[ERROR] Fehler bei {pdf_path.name}: {e}")
            errors += 1
    
    # Verarbeite Bilder direkt
    for i, image_path in enumerate(image_files, len(pdf_files) + 1):
        try:
            logger.info(f"[{i}/{total}] {image_path.name}")
            await process_new_document(image_path)
            processed += 1
        except Exception as e:
            logger.error(f"[ERROR] Fehler bei {image_path.name}: {e}")
            errors += 1
    
    logger.success(f"[OK] Batch-Verarbeitung abgeschlossen: {processed}/{total} Dateien ({errors} Fehler)")

if __name__ == "__main__":
    asyncio.run(process_all_inbox_files())
