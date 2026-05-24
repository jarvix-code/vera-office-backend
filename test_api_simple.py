#!/usr/bin/env python3
"""Test VERA Module API (urllib only)"""
import urllib.request
import json

BASE_URL = "http://localhost:8000"

print("VERA Modul-API Test")
print("=" * 60)

# Test 1: GET /api/modules
print("\n1. GET /api/modules")
try:
    with urllib.request.urlopen(f"{BASE_URL}/api/modules") as r:
        data = json.loads(r.read().decode())
        print(f"Status: {r.status}")
        print(f"Module: {json.dumps(data, indent=2)}")
except Exception as e:
    print(f"Fehler: {e}")

# Test 2: Health
print("\n2. GET /health")
try:
    with urllib.request.urlopen(f"{BASE_URL}/health") as r:
        data = json.loads(r.read().decode())
        print(f"Status: {r.status}")
        print(f"Response: {json.dumps(data, indent=2)}")
except Exception as e:
    print(f"Fehler: {e}")

print("\n" + "=" * 60)
