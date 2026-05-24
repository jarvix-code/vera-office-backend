import requests
import json

# Login
response = requests.post(
    "http://localhost:8000/api/auth/login",
    json={"username": "admin", "password": "admin"}
)
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Rufe /api/modules ab
resp = requests.get("http://localhost:8000/api/modules", headers=headers)
print("=== /api/modules Response ===")
print(f"Status: {resp.status_code}")
print(json.dumps(resp.json(), indent=2))
