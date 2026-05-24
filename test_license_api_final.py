#!/usr/bin/env python3
"""Test Lizenz-Aktivierung via API (finale Version)"""
import urllib.request
import urllib.parse
import json

BASE_URL = "http://localhost:8000"

# Neue Schlüssel (mit Punkt-Delimiter)
ERP_KEY = "VERA-ERP-eyJt-b2Qi-OiJl-cnAi-LCJl-eHAi-Om51-bGws-Imlz-cyI6-InZl-cmEi-fQ.W-21py-Vpyk-X8wU-0Nep-UoCx-7_Qr-Ili3-OIgH-4QDA-ldGE-XoKq-3_OQ-VCOS-gWVd-cFeP-WQCf-aCfW-zK64-IhK7-94OO-1UTB-Q"
TEST_KEY = "VERA-TEST-eyJt-b2Qi-OiJ0-ZXN0-Iiwi-ZXhw-Ijoi-MjAy-MC0w-MS0w-MSIs-Imlz-cyI6-InZl-cmEi-fQ.7--ONl-fDmL--tHf-iEu0-3I7M-X-hM-Fcv7-MSfR-VKp6-bU6y-3ALv-BD8o-CsGS-ipZ7-GVN5-TKIW-UBIS-OJRL-WJqR-bORG-sTQA-Q"

print("=" * 80)
print("VERA Lizenz-API Test (finale Version)")
print("=" * 80)

# Test 1: ERP Lizenz aktivieren
print("\n1. POST /api/modules/license (ERP - unbefristet)")
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
    error_data = json.loads(e.read().decode())
    print(f"ERROR HTTP {e.code}:")
    print(f"  {json.dumps(error_data, indent=2)}")
except Exception as e:
    print(f"ERROR: {e}")

# Test 2: Abgelaufene Lizenz (sollte fehlschlagen)
print("\n2. POST /api/modules/license (TEST - abgelaufen)")
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
    print(f"  {json.dumps(error_data, indent=2)}")
except Exception as e:
    print(f"Fehler: {e}")

# Test 3: Modul-Liste abrufen
print("\n3. GET /api/modules")
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
