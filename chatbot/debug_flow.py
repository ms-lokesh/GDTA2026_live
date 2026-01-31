"""Debug script to trace registration flow"""
import requests
import json

BASE_URL = "http://localhost:5000"

def submit(session_id, answer):
    resp = requests.post(f"{BASE_URL}/api/register/answer", json={
        "session_id": session_id,
        "answer": answer
    })
    data = resp.json()
    step = data.get("state", {}).get("current_step") or "None"
    success = data.get("success", False)
    error = data.get("message", "")
    print(f"Answer: {answer:25s} -> Step: {step:15s} Success: {success} | {error[:50]}")
    return data

# Start session
print("="*60)
print("TESTING INDIA FLOW (Should be: COUNTRY -> STATE -> EMAIL -> REVIEW)")
print("="*60)
start = requests.post(f"{BASE_URL}/api/register/start", json={}).json()
print(f"Start response keys: {start.keys()}")
if "session_id" not in start:
    print(f"ERROR: No session_id in response! Response: {json.dumps(start, indent=2)}")
    exit(1)
sid = start["session_id"]
print(f"Session: {sid}")
print(f"First step: {start['question']['field']}")
print()

# Submit answers
print("\nSubmitting CONSENT:")
r = submit(sid, "Yes")  # CONSENT
print(f"Full response: {json.dumps(r, indent=2)[:300]}\n")
submit(sid, "Test User")  # NAME
submit(sid, "Test Institute")  # INSTITUTION
submit(sid, "Student")  # ROLE
submit(sid, "No")  # GDTA_MEMBER
submit(sid, "No")  # GDTA_AFFILIATION
submit(sid, "India")  # COUNTRY - should go to STATE
submit(sid, "Tamil Nadu")  # STATE - should go to EMAIL
submit(sid, "test@example.com")  # EMAIL - should go to REVIEW

print("\n" + "="*60)
print("TESTING USA FLOW (Should be: COUNTRY -> EMAIL -> REVIEW)")
print("="*60)
start = requests.post(f"{BASE_URL}/api/register/start", json={}).json()
sid = start["session_id"]
print(f"Session: {sid}\n")

submit(sid, "Yes")  # CONSENT
submit(sid, "Test User")  # NAME
submit(sid, "Test Institute")  # INSTITUTION
submit(sid, "Student")  # ROLE
submit(sid, "No")  # GDTA_MEMBER
submit(sid, "No")  # GDTA_AFFILIATION
submit(sid, "USA")  # COUNTRY - should go to EMAIL (skip STATE)
submit(sid, "test@example.com")  # EMAIL - should go to REVIEW
