"""
Test available routes
"""
import requests

def test_routes():
    """Test if routes are available."""
    
    routes_to_test = [
        ("GET", "http://localhost:8000/health"),
        ("GET", "http://localhost:8000/api/docs"),
        ("POST", "http://localhost:8000/api/agent/chat"),
        ("GET", "http://localhost:8000/api/onboarding/status"),
    ]
    
    for method, url in routes_to_test:
        try:
            if method == "GET":
                response = requests.get(url, timeout=5)
            else:
                response = requests.post(url, json={"message": "test"}, timeout=5)
            
            print(f"{method} {url}: {response.status_code}")
            if response.status_code < 400:
                print(f"  ✓ Success")
            else:
                print(f"  ✗ Error: {response.text[:100]}")
        except Exception as e:
            print(f"{method} {url}: ERROR - {e}")

if __name__ == "__main__":
    test_routes()
