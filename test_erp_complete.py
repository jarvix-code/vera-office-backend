import requests

# Login
response = requests.post(
    "http://localhost:8000/api/auth/login",
    json={"username": "admin", "password": "admin"}
)
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Test ERP Endpoints mit korrekten Parametern
erp_tests = [
    ("GET", "/api/modules/erp/dashboard?start=2026-01-01&end=2026-12-31", None),
    ("GET", "/api/modules/erp/items", None),
    ("GET", "/api/modules/erp/stats", None),
    ("GET", "/api/modules/erp/open-items", None)
]

print("=== ERP Module Tests ===")
for method, endpoint, data in erp_tests:
    try:
        if method == "GET":
            resp = requests.get(f"http://localhost:8000{endpoint}", headers=headers)
        else:
            resp = requests.post(f"http://localhost:8000{endpoint}", headers=headers, json=data)
        
        print(f"✅ {method} {endpoint}: {resp.status_code}")
        if resp.status_code >= 400:
            print(f"   Error: {resp.text[:100]}")
    except Exception as e:
        print(f"❌ {method} {endpoint}: {e}")
