"""
Test script for conversation memory functionality
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def test_conversation():
    """Test the conversation flow with memory"""
    print("=" * 60)
    print("Testing Conversation Memory")
    print("=" * 60)
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    # Test 1: User requests schedule as student
    print("\n[TEST 1] User: 'I need a schedule as a student'")
    response = session.post(
        f"{BASE_URL}/api/chat",
        json={"message": "I need a schedule as a student"},
        headers={"Content-Type": "application/json"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response JSON: {response.json()}")
    result = response.json()
    print(f"Response: {result.get('message', 'NO MESSAGE')[:200]}...")
    print(f"Action: {result.get('action')}")
    print(f"Session ID: {result.get('session_id')}")
    
    # Test 2: User modifies to 3 sessions per day
    print("\n[TEST 2] User: 'can you make it 3 sessions per day?'")
    response = session.post(
        f"{BASE_URL}/api/chat",
        json={"message": "can you make it 3 sessions per day?"},
        headers={"Content-Type": "application/json"}
    )
    result = response.json()
    print(f"Response: {result['message'][:200]}...")
    print(f"Action: {result.get('action')}")
    
    # Verify bot didn't ask "are you student or industry?"
    if "student or industry" in result['message'].lower() or "are you a student" in result['message'].lower():
        print("❌ FAILED: Bot asked for user type again (lost context)")
        print(f"Full response: {result['message']}")
    else:
        print("✅ PASSED: Bot remembered user is a student")
        print(f"Bot correctly modified schedule with context")
    
    # Test 3: User changes schedule again
    print("\n[TEST 3] User: 'change it to 2 days'")
    response = session.post(
        f"{BASE_URL}/api/chat",
        json={"message": "change it to 2 days"},
        headers={"Content-Type": "application/json"}
    )
    result = response.json()
    print(f"Response: {result['message'][:200]}...")
    print(f"Action: {result.get('action')}")
    
    # Verify bot used stored context
    if "student or industry" in result['message'].lower():
        print("❌ FAILED: Bot asked for user type again")
    else:
        print("✅ PASSED: Bot maintained context across multiple turns")
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_conversation()
    except Exception as e:
        print(f"Error: {e}")
