"""Test VERA OCR Tool"""
import sys
sys.path.insert(0, 'C:/Jarvix/vera-office')

import requests

# Trigger OCR for all QM docs
response = requests.post(
    "http://127.0.0.1:8000/api/qm/ocr",
    json={"process_all": True}
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

# Check status
import time
time.sleep(2)

status_response = requests.get("http://127.0.0.1:8000/api/qm/ocr/status")
print(f"\nOCR Status: {status_response.json()}")
