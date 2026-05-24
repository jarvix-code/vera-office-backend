import json
from pathlib import Path

# Lizenz-Datei laden
license_path = Path("C:/Jarvix/vera-office/data/licenses.json")
with open(license_path, 'r') as f:
    licenses = json.load(f)

print("Vorher:")
print(f"ERP: {licenses['erp'][:50]}...")

# ERP-Key entchunken (alle '-' nach VERA-ERP- entfernen)
erp_key = licenses['erp']
# Splitte bei erstem '-' nach Modul-Name
prefix, body = erp_key.split('-', 2)[:2], erp_key.split('-', 2)[2]
# Entferne alle '-' aus dem Body
body_clean = body.replace('-', '')
# Setze wieder zusammen
erp_key_clean = f"VERA-ERP-{body_clean}"

licenses['erp'] = erp_key_clean

print("\nNachher:")
print(f"ERP: {erp_key_clean[:50]}...")

# Speichern
with open(license_path, 'w') as f:
    json.dump(licenses, f, indent=2)

print("\n✅ Lizenz-Datei aktualisiert!")
