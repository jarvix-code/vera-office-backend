"""Test duplicate detection."""
import sys
sys.path.insert(0, 'C:/Jarvix/vera-office')

from backend.core.duplicate_handler import check_duplicate
from backend.db.database import SessionLocal
from backend.models.document import Document

db = SessionLocal()

# Get first document
doc = db.query(Document).first()

if not doc:
    print("❌ No documents in database - cannot test")
    sys.exit(1)

print(f"✅ Testing with: {doc.filename}")
print(f"   OCR Text Length: {len(doc.ocr_text) if doc.ocr_text else 0}")

# Test duplicate detection with same text
if doc.ocr_text:
    duplicate = check_duplicate(doc.ocr_text, db)
    
    if duplicate:
        print(f"✅ DUPLICATE DETECTED: {duplicate.filename}")
    else:
        print("❌ No duplicate found (should find itself!)")
else:
    print("⚠️  Document has no OCR text")

db.close()
print("\n✅ Duplicate detection system ready!")
