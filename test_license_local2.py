#!/usr/bin/env python3
"""Test Lizenz-Validierung lokal (neue Schlüssel)"""
from backend.modules.license import LicenseStore
from pathlib import Path

# Public Key laden
pub_key_path = Path("backend/config/vera_license.pub")
pub_pem = pub_key_path.read_text()

# LicenseStore initialisieren
store = LicenseStore(Path("data/test_licenses2.json"), pub_pem)

# Neue Schlüssel (mit Punkt-Delimiter)
ERP_KEY = "VERA-ERP-eyJt-b2Qi-OiJl-cnAi-LCJl-eHAi-Om51-bGws-Imlz-cyI6-InZl-cmEi-fQ.W-21py-Vpyk-X8wU-0Nep-UoCx-7_Qr-Ili3-OIgH-4QDA-ldGE-XoKq-3_OQ-VCOS-gWVd-cFeP-WQCf-aCfW-zK64-IhK7-94OO-1UTB-Q"
TEST_KEY = "VERA-TEST-eyJt-b2Qi-OiJ0-ZXN0-Iiwi-ZXhw-Ijoi-MjAy-MC0w-MS0w-MSIs-Imlz-cyI6-InZl-cmEi-fQ.7--ONl-fDmL--tHf-iEu0-3I7M-X-hM-Fcv7-MSfR-VKp6-bU6y-3ALv-BD8o-CsGS-ipZ7-GVN5-TKIW-UBIS-OJRL-WJqR-bORG-sTQA-Q"

print("=" * 80)
print("Lokale Lizenz-Validierung (neues Format)")
print("=" * 80)

# Test 1: ERP Lizenz
print("\n1. ERP Lizenz (unbefristet)")
print("-" * 80)
success, msg = store.activate(ERP_KEY)
print(f"Erfolg: {success}")
print(f"Nachricht: {msg}")

if success:
    print(f"Lizenzstatus: {store.get_status('erp')}")
    print(f"Lizenziert: {store.is_licensed('erp')}")

# Test 2: Test Lizenz (abgelaufen)
print("\n2. Test Lizenz (abgelaufen)")
print("-" * 80)
success, msg = store.activate(TEST_KEY)
print(f"Erfolg: {success}")
print(f"Nachricht: {msg}")

if not success:
    print("OK - Erwarteter Fehler")

print("\n" + "=" * 80)
