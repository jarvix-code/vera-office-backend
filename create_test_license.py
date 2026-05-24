#!/usr/bin/env python3
"""Erstellt Test-Lizenzschlüssel für ERP Modul"""
from backend.modules.license import create_license_key
from datetime import date
from pathlib import Path

# Private Key laden
key_path = Path("backend/config/vera_license.key")
if not key_path.exists():
    print("❌ Private Key nicht gefunden!")
    print("Bitte 'python -m backend.modules.keygen' ausführen")
    exit(1)

priv_pem = key_path.read_text()

# Lizenzschlüssel für ERP erstellen (unbefristet)
erp_key = create_license_key(priv_pem, module="erp", expiry=None)
print(f"ERP Lizenz (unbefristet):\n{erp_key}")

# Lizenzschlüssel für QM erstellen (1 Jahr gültig)
qm_key = create_license_key(priv_pem, module="qm", expiry=date(2027, 2, 22))
print(f"\nQM Lizenz (gültig bis 2027-02-22):\n{qm_key}")

# Test-Modul (abgelaufen)
test_key = create_license_key(priv_pem, module="test", expiry=date(2020, 1, 1))
print(f"\nTest Lizenz (ABGELAUFEN):\n{test_key}")
