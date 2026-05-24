"""
Detailed test of chat endpoint
"""
import requests
import json

def test_chat_endpoint():
    """Test chat endpoint with details."""
    
    url = "http://localhost:8000/api/agent/chat"
    payload = {
        "message": "Hallo",
        "session_id": "test123"
    }
    
    print(f"Testing: POST {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()
    
    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_chat_endpoint()
