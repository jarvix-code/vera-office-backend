#!/usr/bin/env python3
"""Test Lizenz-Aktivierung"""
import urllib.request
import urllib.parse
import json

BASE_URL = "http://localhost:8000"

# ERP Lizenz (unbefristet)
ERP_KEY = "VERA-ERP-eyJt-b2Qi-OiJl-cnAi-LCJl-eHAi-Om51-bGws-Imlz-cyI6-InZl-cmEi-fQW2-1pyV-pykX-8wU0-NepU-oCx7-_QrI-li3O-IgH4-QDAl-dGEX-oKq3-_OQV-COSg-WVdc-FePW-QCfa-CfWz-K64I-hK79-4OO1-UTBQ"

# Test Lizenz (abgelaufen)
TEST_KEY = "VERA-TEST-eyJt-b2Qi-OiJ0-ZXN0-Iiwi-ZXhw-Ijoi-MjAy-MC0w-MS0w-MSIs-Imlz-cyI6-InZl-cmEi-fQ7--ONlf-DmL--tHfi-Eu03-I7MX--hMF-cv7M-SfRV-Kp6b-U6y3-ALvB-D8oC-sGSi-pZ7G-VN5T-KIWU-BISO-JRLW-JqRb-ORGs-TQAQ"

print("=" * 80)
print("VERA Lizenz-Aktivierungs-Test")
print("=" * 80)

# Test 1: ERP Lizenz aktivieren
print("\n1. POST /api/modules/license (ERP - gueltig)")
print("-" * 80)
try:
    data = json.dumps({"key": ERP_KEY}).encode('utf-8')
    req = urllib.request.Request(
        f"{BASE_URL}/api/modules/license",
        data=data,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req) as r:
        response = json.loads(r.read().decode())
        print(f"OK Status: {r.status}")
        print(f"Response: {json.dumps(response, indent=2)}")
except urllib.error.HTTPError as e:
    print(f"ERROR HTTP {e.code}: {e.read().decode()}")
except Exception as e:
    print(f"ERROR: {e}")

# Test 2: Modul-Liste abrufen (sollte jetzt ERP enthalten)
print("\n2. GET /api/modules (nach ERP-Aktivierung)")
print("-" * 80)
try:
    with urllib.request.urlopen(f"{BASE_URL}/api/modules") as r:
        modules = json.loads(r.read().decode())
        print(f"Status: {r.status}")
        print(f"Module: {json.dumps(modules, indent=2)}")
except Exception as e:
    print(f"Fehler: {e}")

# Test 3: Abgelaufene Lizenz aktivieren (sollte fehlschlagen)
print("\n3. POST /api/modules/license (TEST - abgelaufen)")
print("-" * 80)
try:
    data = json.dumps({"key": TEST_KEY}).encode('utf-8')
    req = urllib.request.Request(
        f"{BASE_URL}/api/modules/license",
        data=data,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req) as r:
        response = json.loads(r.read().decode())
        print(f"Status: {r.status}")
        print(f"Response: {json.dumps(response, indent=2)}")
except urllib.error.HTTPError as e:
    error_data = json.loads(e.read().decode())
    print(f"OK Erwarteter Fehler HTTP {e.code}:")
    print(f"   {json.dumps(error_data, indent=2)}")
except Exception as e:
    print(f"Fehler: {e}")

# Test 4: Lizenz deaktivieren
print("\n4. DELETE /api/modules/license/erp")
print("-" * 80)
try:
    req = urllib.request.Request(
        f"{BASE_URL}/api/modules/license/erp",
        method='DELETE'
    )
    with urllib.request.urlopen(req) as r:
        response = json.loads(r.read().decode())
        print(f"OK Status: {r.status}")
        print(f"Response: {json.dumps(response, indent=2)}")
except urllib.error.HTTPError as e:
    print(f"ERROR HTTP {e.code}: {e.read().decode()}")
except Exception as e:
    print(f"ERROR: {e}")

# Test 5: Modul-Liste nach Deaktivierung
print("\n5. GET /api/modules (nach Deaktivierung)")
print("-" * 80)
try:
    with urllib.request.urlopen(f"{BASE_URL}/api/modules") as r:
        modules = json.loads(r.read().decode())
        print(f"Status: {r.status}")
        print(f"Module: {json.dumps(modules, indent=2)}")
except Exception as e:
    print(f"Fehler: {e}")

print("\n" + "=" * 80)
print("Tests abgeschlossen")
print("=" * 80)
