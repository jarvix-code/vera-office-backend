"""
Test conversational onboarding
"""
import requests
import json

API_URL = "http://localhost:8000/api/agent/chat"

def test_chat(message, session_id="test_onboarding"):
    """Send a chat message and print response."""
    payload = {
        "message": message,
        "session_id": session_id
    }
    
    try:
        response = requests.post(API_URL, json=payload, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        print(f"\n{'='*60}")
        print(f"USER: {message}")
        print(f"{'='*60}")
        print(f"VERA: {data.get('response', '')}")
        if data.get('suggestions'):
            print(f"\nSuggestions: {', '.join(data['suggestions'])}")
        print(f"{'='*60}\n")
        
        return data
    except Exception as e:
        print(f"Error: {e}")
        return None

def run_full_onboarding():
    """Run a complete onboarding flow."""
    print("Starting conversational onboarding test...\n")
    
    # 1. Trigger greeting (empty message)
    test_chat(" ")
    
    # 2. Company name
    test_chat("Zahnarztpraxis Dr. Müller")
    
    # 3. Company type (should be auto-detected)
    test_chat("Zahnarztpraxis")
    
    # 4. Employee count
    test_chat("12 Mitarbeiter")
    
    # 5. Document types
    test_chat("Ja, so übernehmen und noch Laboraufträge")
    
    # 6. Network
    test_chat("Ja")
    
    # 7. Confirm
    test_chat("Stimmt!")
    
    print("\nOnboarding test completed!")

if __name__ == "__main__":
    run_full_onboarding()
