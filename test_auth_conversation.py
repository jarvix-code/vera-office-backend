"""
Test script for AuthConversation (without database)
"""
from backend.core.ai.auth_conversation import AuthConversation, AuthState


def test_state_machine():
    """Test auth conversation state machine (mocked, no DB)."""
    
    print("=" * 60)
    print("AUTH CONVERSATION TEST (State Machine Only)")
    print("=" * 60)
    
    # Initialize conversation (no DB)
    conv = AuthConversation()
    
    # Test 1: GREETING state
    print("\n1. GREETING State:")
    print(f"   State: {conv.current_state}")
    print(f"   Message: {conv.get_message()}")
    assert conv.current_state == AuthState.GREETING
    
    # Test 2: Process input in GREETING (should move to USERNAME)
    print("\n2. Process 'Hallo' (should move to USERNAME):")
    result = conv.process_input("Hallo", db=None)
    print(f"   State: {conv.current_state}")
    print(f"   Response: {result['message']}")
    assert conv.current_state == AuthState.USERNAME
    
    # Test 3: Invalid username (greeting word)
    print("\n3. Process 'Hi' (should stay in USERNAME - validation failed):")
    result = conv.process_input("Hi", db=None)
    print(f"   State: {conv.current_state}")
    print(f"   Response: {result['message']}")
    assert conv.current_state == AuthState.USERNAME
    assert "gültigen Benutzernamen" in result['message']
    
    # Test 4: Valid username format (but DB lookup will fail without DB)
    print("\n4. Process 'boris' (valid format, but no DB for lookup):")
    result = conv.process_input("boris", db=None)
    print(f"   State: {conv.current_state}")
    print(f"   Response: {result['message']}")
    # Without DB, should fail with "Systemfehler"
    assert "Systemfehler" in result['message']
    
    print("\n" + "=" * 60)
    print("STATE MACHINE TEST: PASSED")
    print("=" * 60)
    print("\nNote: Full auth flow requires database connection.")
    print("      Use backend test suite for end-to-end tests.")


if __name__ == "__main__":
    test_state_machine()
