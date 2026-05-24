import requests

# Login
response = requests.post(
    "http://localhost:8000/api/auth/login",
    json={"username": "admin", "password": "admin"}
)
print(f"Login: {response.status_code}")
token = response.json()["access_token"]
print(f"Token: {token[:30]}...")

# Test geschützte Endpoints
headers = {"Authorization": f"Bearer {token}"}

endpoints = [
    "/api/system/brain-stats",
    "/api/documents/list",
    "/api/system/update-status"
]

for endpoint in endpoints:
    resp = requests.get(f"http://localhost:8000{endpoint}", headers=headers)
    print(f"{endpoint}: {resp.status_code}")
    if resp.status_code != 200:
        print(f"  Error: {resp.text[:100]}")
