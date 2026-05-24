#!/usr/bin/env python3
"""Debug Lizenzschlüssel-Format"""
import re
import base64
import json

# Test Lizenz (abgelaufen)
TEST_KEY = "VERA-TEST-eyJt-b2Qi-OiJ0-ZXN0-Iiwi-ZXhw-Ijoi-MjAy-MC0w-MS0w-MSIs-Imlz-cyI6-InZl-cmEi-fQ7--ONlf-DmL--tHfi-Eu03-I7MX--hMF-cv7M-SfRV-Kp6b-U6y3-ALvB-D8oC-sGSi-pZ7G-VN5T-KIWU-BISO-JRLW-JqRb-ORGs-TQAQ"

print("Debug Lizenzschlüssel")
print("=" * 80)

# Regex
match = re.match(r'^VERA-([A-Z]+)-(.+)$', TEST_KEY, re.IGNORECASE)
if not match:
    print("Regex fehlgeschlagen!")
    exit(1)

module_name = match.group(1).lower()
body = match.group(2)

print(f"Modul: {module_name}")
print(f"Body (chunked): {body[:50]}...")

# Entchunken
body = body.replace('-', '')
print(f"Body (dechunked): {body[:50]}...")
print(f"Body Länge: {len(body)}")

# Splitten (letzten 86 Zeichen = Signatur)
if len(body) < 86:
    print("Zu kurz!")
    exit(1)

payload_b64 = body[:-86]
sig_b64 = body[-86:]

print(f"\nPayload base64 ({len(payload_b64)} Zeichen):")
print(f"  {payload_b64}")
print(f"\nSignatur base64 ({len(sig_b64)} Zeichen):")
print(f"  {sig_b64[:40]}...")

# Base64url-Decode
try:
    # Padding hinzufügen
    payload_bytes = base64.urlsafe_b64decode(payload_b64 + '==')
    print(f"\nPayload Bytes ({len(payload_bytes)} bytes):")
    print(f"  {payload_bytes}")
    
    # Payload parsen
    payload = json.loads(payload_bytes)
    print(f"\nPayload JSON:")
    print(f"  {json.dumps(payload, indent=2)}")
    
except Exception as e:
    print(f"\nFEHLER: {e}")
    print("\nVersuch ohne Padding:")
    try:
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        print(f"Payload Bytes ({len(payload_bytes)} bytes):")
        print(f"  {payload_bytes}")
        payload = json.loads(payload_bytes)
        print(f"Payload JSON:")
        print(f"  {json.dumps(payload, indent=2)}")
    except Exception as e2:
        print(f"Auch fehlgeschlagen: {e2}")
