#!/usr/bin/env python3
"""Test VERA Module API"""
import requests
import json

BASE_URL = "http://localhost:8000"

print("=" * 60)
print("VERA Modul-API Test")
print("=" * 60)

# Test 1: GET /api/modules (Liste aller Module)
print("\n1. GET /api/modules (Modul-Liste)")
print("-" * 60)
try:
    r = requests.get(f"{BASE_URL}/api/modules")
    print(f"Status: {r.status_code}")
    modules = r.json()
    print(f"Module: {json.dumps(modules, indent=2)}")
except Exception as e:
    print(f"Fehler: {e}")

# Test 2: Health Check
print("\n2. GET /health")
print("-" * 60)
try:
    r = requests.get(f"{BASE_URL}/health")
    print(f"Status: {r.status_code}")
    print(f"Response: {r.json()}")
except Exception as e:
    print(f"Fehler: {e}")

print("\n" + "=" * 60)
print("Tests abgeschlossen")
print("=" * 60)
