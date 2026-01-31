"""Quick test for TC-10 and TC-14 only"""
import requests
import json

BASE_URL = "http://localhost:5000"

def start_session():
    """Start a new registration session"""
    response = requests.post(f"{BASE_URL}/api/register/start", json={})
    data = response.json()
    session_id = data.get("session_id")
    return session_id, data

def submit_answer(session_id, answer):
    """Submit an answer to the registration system"""
    response = requests.post(
        f"{BASE_URL}/api/register/answer",
        json={"session_id": session_id, "answer": answer}
    )
    return response.json()

print("="*80)
print("TESTING TC-10: CANCEL REGISTRATION")
print("="*80)

session_id, start_data = start_session()
print(f"Session created: {session_id}")

resp1 = submit_answer(session_id, "Yes")
print(f"Consent: Success={resp1.get('success')}, Step={resp1.get('state', {}).get('current_step')}")

resp2 = submit_answer(session_id, "Test User")
print(f"Name: Success={resp2.get('success')}, Step={resp2.get('state', {}).get('current_step')}")

# Cancel
print("\nAttempting to cancel...")
print(f"Using session_id: {session_id}")

# First verify session still exists
status_resp = requests.get(f"{BASE_URL}/api/register/status?session_id={session_id}")
print(f"Status check: {status_resp.status_code} - {status_resp.json()}")

response = requests.post(f"{BASE_URL}/api/register/cancel", json={"session_id": session_id})
data = response.json()
print(f"Cancel response: {json.dumps(data, indent=2)}")

if data.get("cancelled") or "cancel" in data.get("message", "").lower():
    print("✅ TC-10 PASS: Cancel worked!")
else:
    print("❌ TC-10 FAIL: Cancel didn't work")

print("\n" + "="*80)
print("TESTING TC-14: STATE AUTO-CLEAR WHEN COUNTRY CHANGES")
print("="*80)

session_id2, _ = start_session()
print(f"Session created: {session_id2}")

# Complete flow to REVIEW with India
submit_answer(session_id2, "Yes")  # Consent
print("✓ Consent")
submit_answer(session_id2, "Test User")
print("✓ Name")
submit_answer(session_id2, "Test Institution")
print("✓ Institution")
submit_answer(session_id2, "Student")
print("✓ Role")
submit_answer(session_id2, "Yes")
print("✓ GDTA Member")
submit_answer(session_id2, "Yes")
print("✓ GDTA Affiliation")
resp_india = submit_answer(session_id2, "India")
print(f"✓ Country: India -> Next step: {resp_india.get('state', {}).get('current_step')}")
resp_state = submit_answer(session_id2, "Karnataka")
print(f"✓ State: Karnataka -> Next step: {resp_state.get('state', {}).get('current_step')}")

# Verify state was stored
state_before = resp_state.get("state", {}).get("data", {}).get("state")
print(f"\nState before editing: {state_before}")

resp_email = submit_answer(session_id2, "test@test.com")
print(f"✓ Email -> Next step: {resp_email.get('state', {}).get('current_step')}")

# Now at REVIEW - edit country
print("\n--- Editing country from India to USA ---")
resp_edit = submit_answer(session_id2, "country")
print(f"Edit country initiated: Step={resp_edit.get('state', {}).get('current_step')}")

resp_usa = submit_answer(session_id2, "USA")
print(f"Changed to USA: Step={resp_usa.get('state', {}).get('current_step')}")

# Check if state was auto-cleared
country_after = resp_usa.get("state", {}).get("data", {}).get("country")
state_after = resp_usa.get("state", {}).get("data", {}).get("state")

print(f"\nAfter changing country:")
print(f"  Country: {country_after}")
print(f"  State: {state_after}")

if state_after is None:
    print("✅ TC-14 PASS: State auto-cleared successfully!")
else:
    print(f"❌ TC-14 FAIL: State should be None but is '{state_after}'")
