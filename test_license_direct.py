from backend.modules.license import LicenseStore
from pathlib import Path

# Lade Public Key
pub_key_path = Path("C:/Jarvix/vera-office/backend/config/vera_license.pub")
with open(pub_key_path, 'r') as f:
    public_key_pem = f.read()

# Erstelle LicenseStore
license_path = Path("C:/Jarvix/vera-office/data/licenses.json")
store = LicenseStore(license_path, public_key_pem)

# Teste beide Module
print("=== Lizenz-Status ===")
print(f"ERP lizenziert: {store.is_licensed('erp')}")
print(f"QM lizenziert: {store.is_licensed('qm')}")

print("\n=== Detaillierter Status ===")
print(f"ERP: {store.get_status('erp')}")
print(f"QM: {store.get_status('qm')}")

print("\n=== Alle Lizenzen ===")
print(store.all_licenses())

# Teste Key-Validierung direkt
import json
with open(license_path, 'r') as f:
    licenses = json.load(f)

print("\n=== Direkte Validierung ===")
for module, key in licenses.items():
    valid, name, msg = store._validate_key(key)
    print(f"{module}: valid={valid}, name={name}, msg={msg}")
    if not valid:
        print(f"  Key: {key[:50]}...")
