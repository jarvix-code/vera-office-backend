import requests
import json

# Health check
print("=== Health Check ===")
r = requests.get("http://127.0.0.1:18793/health")
print(json.dumps(r.json(), indent=2))

# Chat test
print("\n=== Chat Test ===")
r = requests.post(
    "http://127.0.0.1:18793/chat",
    json={
        "message": "Was ist Hygiene-Management?",
        "max_tokens": 128,
        "temperature": 0.7
    }
)
print(json.dumps(r.json(), indent=2))
