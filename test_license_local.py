#!/usr/bin/env python3
"""Test Lizenz-Validierung lokal"""
from backend.modules.license import LicenseStore
from pathlib import Path

# Public Key laden
pub_key_path = Path("backend/config/vera_license.pub")
pub_pem = pub_key_path.read_text()

# LicenseStore initialisieren
store = LicenseStore(Path("data/test_licenses.json"), pub_pem)

# ERP Lizenz (unbefristet)
ERP_KEY = "VERA-ERP-eyJt-b2Qi-OiJl-cnAi-LCJl-eHAi-Om51-bGws-Imlz-cyI6-InZl-cmEi-fQW2-1pyV-pykX-8wU0-NepU-oCx7-_QrI-li3O-IgH4-QDAl-dGEX-oKq3-_OQV-COSg-WVdc-FePW-QCfa-CfWz-K64I-hK79-4OO1-UTBQ"

# Test Lizenz (abgelaufen)
TEST_KEY = "VERA-TEST-eyJt-b2Qi-OiJ0-ZXN0-Iiwi-ZXhw-Ijoi-MjAy-MC0w-MS0w-MSIs-Imlz-cyI6-InZl-cmEi-fQ7--ONlf-DmL--tHfi-Eu03-I7MX--hMF-cv7M-SfRV-Kp6b-U6y3-ALvB-D8oC-sGSi-pZ7G-VN5T-KIWU-BISO-JRLW-JqRb-ORGs-TQAQ"

print("=" * 80)
print("Lokale Lizenz-Validierung")
print("=" * 80)

# Test 1: ERP Lizenz
print("\n1. ERP Lizenz (unbefristet)")
print("-" * 80)
success, msg = store.activate(ERP_KEY)
print(f"Erfolg: {success}")
print(f"Nachricht: {msg}")

if success:
    print(f"\nLizenzstatus: {store.get_status('erp')}")
    print(f"Lizenziert: {store.is_licensed('erp')}")

# Test 2: Test Lizenz (abgelaufen)
print("\n2. Test Lizenz (abgelaufen)")
print("-" * 80)
success, msg = store.activate(TEST_KEY)
print(f"Erfolg: {success}")
print(f"Nachricht: {msg}")

if not success:
    print("OK - Erwarteter Fehler (abgelaufen)")

# Test 3: Ungültiger Schlüssel
print("\n3. Ungültiger Schlüssel")
print("-" * 80)
success, msg = store.activate("VERA-FAKE-invalid-key-data")
print(f"Erfolg: {success}")
print(f"Nachricht: {msg}")

print("\n" + "=" * 80)
