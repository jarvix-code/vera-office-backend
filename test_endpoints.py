import requests

# Login
response = requests.post(
    "http://localhost:8000/api/auth/login",
    json={"username": "admin", "password": "admin"}
)
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Test POST /api/system/check-update
print("Testing POST /api/system/check-update...")
try:
    resp = requests.post("http://localhost:8000/api/system/check-update", headers=headers)
    print(f"  Status: {resp.status_code}")
    if resp.status_code == 200:
        print(f"  Response: {resp.json()}")
except Exception as e:
    print(f"  Error: {e}")

# Test Modul-Endpoints (ERP + QM)
print("\nTesting Module Endpoints...")
module_endpoints = [
    ("GET", "/api/modules"),
    ("GET", "/api/modules/erp/dashboard"),
    ("GET", "/api/modules/qm/dashboard")
]

for method, endpoint in module_endpoints:
    try:
        if method == "GET":
            resp = requests.get(f"http://localhost:8000{endpoint}", headers=headers)
        else:
            resp = requests.post(f"http://localhost:8000{endpoint}", headers=headers)
        print(f"{method} {endpoint}: {resp.status_code}")
        if resp.status_code >= 400:
            print(f"  Error: {resp.text[:150]}")
    except Exception as e:
        print(f"{method} {endpoint}: Error - {e}")
