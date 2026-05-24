import sys
sys.path.insert(0, 'C:/Jarvix/vera-office')
sys.path.insert(0, 'C:/Jarvix/vera-office/backend')

from backend.core.ai.safe_classifier import SafeClassifier
from backend.db.database import SessionLocal
from backend.models.document import Document

# Get first document
db = SessionLocal()
doc = db.query(Document).first()

if not doc:
    print('Keine Dokumente gefunden!')
    exit(1)

print(f'Dokument: {doc.filename}')
print(f'OCR Text: {len(doc.ocr_text or "")} Zeichen')

# Klassifiziere
try:
    classifier = SafeClassifier()
    
    # Mock User für Test
    class MockUser:
        first_name = 'Boris'
        id = 1
    
    result = classifier.classify_with_confidence_levels(doc, MockUser())
    
    print('')
    print('=== KLASSIFIKATIONS-RESULT ===')
    action = result.get('action')
    confidence = result.get('confidence', 0)
    
    print(f'Action: {action}')
    print(f'Confidence: {confidence:.2%}')
    
    if action == 'auto_classified':
        cls = result.get('class')
        print(f'Klasse: {cls}')
        print('→ Auto-klassifiziert (>=95%)')
    
    elif action == 'confirm_with_suggestion':
        vorschlag = result.get('vorschlag')
        frage = result.get('frage')
        print(f'Vorschlag: {vorschlag}')
        print(f'Frage: {frage}')
        print('→ Quick Confirm (75-95%)')
    
    else:
        frage = result.get('frage')
        print(f'Frage: {frage}')
        print('→ Volle Erklärung (<75%)')

except Exception as e:
    print(f'Fehler: {e}')
    import traceback
    traceback.print_exc()

db.close()
