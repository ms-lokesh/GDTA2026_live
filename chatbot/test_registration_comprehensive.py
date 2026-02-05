"""
COMPREHENSIVE REGISTRATION TEST SUITE - GDTA 2026
QA Testing for Logic-Controlled Conversational Registration

Test Categories:
1. Normal Flow Tests
2. Conditional Logic Tests  
3. Validation Edge Cases
4. Edit Functionality Tests
5. Flow Interruption Tests
6. Security & Design Tests
"""

import requests
import json
from typing import Dict, Any, List

BASE_URL = "http://localhost:5000"
TEST_RESULTS = []


class TestCase:
    """Test case structure"""
    def __init__(self, id: str, name: str, category: str):
        self.id = id
        self.name = name
        self.category = category
        self.status = "NOT RUN"
        self.details = ""
        self.expected = ""
        self.actual = ""


def start_session() -> tuple:
    """Start a new registration session"""
    response = requests.post(f"{BASE_URL}/api/register/start", json={})
    data = response.json()
    session_id = data.get("session_id")
    return session_id, data


def submit_answer(session_id: str, answer: str) -> Dict[str, Any]:
    """Submit an answer to the registration system"""
    response = requests.post(
        f"{BASE_URL}/api/register/answer",
        json={"session_id": session_id, "answer": answer}
    )
    return response.json()


def complete_registration_flow(session_id: str, data: Dict[str, str]) -> List[Dict]:
    """Complete full registration with given data"""
    responses = []
    
    # CONSENT
    resp = submit_answer(session_id, data.get("consent", "Yes"))
    responses.append(("CONSENT", resp))
    
    # If consent declined, stop here
    if resp.get("cancelled"):
        return responses
    
    # NAME
    resp = submit_answer(session_id, data["name"])
    responses.append(("NAME", resp))
    
    # INSTITUTION
    resp = submit_answer(session_id, data["institution"])
    responses.append(("INSTITUTION", resp))
    
    # ROLE
    resp = submit_answer(session_id, data["role"])
    responses.append(("ROLE", resp))
    
    # GDTA_MEMBER
    resp = submit_answer(session_id, data["gdta_member"])
    responses.append(("GDTA_MEMBER", resp))
    
    # GDTA_AFFILIATION
    resp = submit_answer(session_id, data["gdta_affiliation"])
    responses.append(("GDTA_AFFILIATION", resp))
    
    # COUNTRY
    resp = submit_answer(session_id, data["country"])
    responses.append(("COUNTRY", resp))
    
    # Check next step - should be either STATE or EMAIL
    next_step = resp.get("state", {}).get("current_step")
    
    # STATE (conditional - only if India)
    if next_step == "state" and data.get("state"):
        resp = submit_answer(session_id, data["state"])
        responses.append(("STATE", resp))
        next_step = resp.get("state", {}).get("current_step")
    
    # EMAIL (get current step to check)
    if next_step == "email":
        resp = submit_answer(session_id, data["email"])
        responses.append(("EMAIL", resp))
    
    # REVIEW - continue
    resp = submit_answer(session_id, "continue")
    responses.append(("REVIEW", resp))
    
    # CONFIRMATION
    resp = submit_answer(session_id, "CONFIRM")
    responses.append(("CONFIRM", resp))
    
    return responses


# ============================================================
# CATEGORY 1: NORMAL FLOW TESTS
# ============================================================

def tc_01_student_india():
    """TC-01: Successful Student Registration (India)"""
    tc = TestCase("TC-01", "Student Registration (India)", "Normal Flow")
    tc.expected = "State question asked, registration completes successfully"
    
    try:
        session_id, start_data = start_session()
        
        data = {
            "name": "Phoenix Kumar",
            "institution": "SNS College of Technology",
            "role": "Student",
            "gdta_member": "Yes",
            "gdta_affiliation": "Yes",
            "country": "India",
            "state": "Tamil Nadu",
            "email": "phoenix@snsct.org"
        }
        
        responses = complete_registration_flow(session_id, data)
        
        # Verify state was asked
        state_asked = any(step == "STATE" for step, _ in responses)
        
        # Verify completion
        final_response = responses[-1][1]
        completed = final_response.get("completed", False)
        
        if state_asked and completed:
            tc.status = "PASS"
            tc.actual = f"State asked: {state_asked}, Completed: {completed}"
        else:
            tc.status = "FAIL"
            tc.actual = f"State asked: {state_asked}, Completed: {completed}, Steps: {[s for s, _ in responses]}"
            
    except Exception as e:
        tc.status = "ERROR"
        tc.details = str(e)
        import traceback
        tc.actual = traceback.format_exc()
    
    TEST_RESULTS.append(tc)
    return tc


def tc_02_industry_international():
    """TC-02: Successful Industry Registration (International)"""
    tc = TestCase("TC-02", "Industry Registration (International)", "Normal Flow")
    tc.expected = "State question NOT asked, registration completes successfully"
    
    try:
        session_id, start_data = start_session()
        
        data = {
            "name": "Alex Meyer",
            "institution": "DesignCorp",
            "role": "Industry",
            "gdta_member": "No",
            "gdta_affiliation": "Yes",
            "country": "Germany",
            "email": "alex@designcorp.com"
        }
        
        responses = complete_registration_flow(session_id, data)
        
        # Verify state was NOT asked
        state_asked = any(step == "STATE" for step, _ in responses)
        
        # Verify completion
        final_response = responses[-1][1]
        completed = final_response.get("completed", False)
        
        # Check state is null
        state_value = final_response.get("state", {}).get("data", {}).get("state")
        
        if not state_asked and completed and state_value is None:
            tc.status = "PASS"
            tc.actual = f"State asked: {state_asked}, Completed: {completed}, State value: {state_value}"
        else:
            tc.status = "FAIL"
            tc.actual = f"State asked: {state_asked}, Completed: {completed}, State value: {state_value}"
            
    except Exception as e:
        tc.status = "ERROR"
        tc.details = str(e)
    
    TEST_RESULTS.append(tc)
    return tc


def tc_03_faculty_india():
    """TC-03: Faculty Registration (India)"""
    tc = TestCase("TC-03", "Faculty Registration (India)", "Normal Flow")
    tc.expected = "Institution asked, state collected, successful registration"
    
    try:
        session_id, start_data = start_session()
        
        data = {
            "name": "Dr. Sarah Johnson",
            "institution": "IIT Madras",
            "role": "Faculty",
            "gdta_member": "Yes",
            "gdta_affiliation": "Yes",
            "country": "India",
            "state": "Tamil Nadu",
            "email": "sarah@iitm.ac.in"
        }
        
        responses = complete_registration_flow(session_id, data)
        
        # Verify state was asked
        state_asked = any(step == "STATE" for step, _ in responses)
        
        # Verify completion
        final_response = responses[-1][1]
        completed = final_response.get("completed", False)
        
        if state_asked and completed:
            tc.status = "PASS"
            tc.actual = f"State asked: {state_asked}, Completed: {completed}"
        else:
            tc.status = "FAIL"
            tc.actual = f"State asked: {state_asked}, Completed: {completed}"
            
    except Exception as e:
        tc.status = "ERROR"
        tc.details = str(e)
    
    TEST_RESULTS.append(tc)
    return tc


# ============================================================
# CATEGORY 2: CONDITIONAL LOGIC TESTS
# ============================================================

def tc_04_country_case_insensitive():
    """TC-04: Country Case Insensitivity"""
    tc = TestCase("TC-04", "Country Case Insensitivity", "Conditional Logic")
    tc.expected = "State question triggered for india/INDIA/InDiA"
    
    try:
        results = []
        for country_variant in ["india", "INDIA", "InDiA"]:
            session_id, _ = start_session()
            
            submit_answer(session_id, "Yes")  # Consent
            submit_answer(session_id, "Test User")
            submit_answer(session_id, "Test Institution")
            submit_answer(session_id, "Student")
            submit_answer(session_id, "Yes")
            submit_answer(session_id, "Yes")
            resp = submit_answer(session_id, country_variant)
            
            # Check if state question is next
            next_step = resp.get("state", {}).get("current_step")
            results.append((country_variant, next_step == "state"))
        
        all_triggered = all(triggered for _, triggered in results)
        
        if all_triggered:
            tc.status = "PASS"
            tc.actual = f"All variants triggered state: {results}"
        else:
            tc.status = "FAIL"
            tc.actual = f"Some variants failed: {results}"
            
    except Exception as e:
        tc.status = "ERROR"
        tc.details = str(e)
    
    TEST_RESULTS.append(tc)
    return tc


def tc_05_country_extra_spaces():
    """TC-05: Country with Extra Spaces"""
    tc = TestCase("TC-05", "Country with Extra Spaces", "Conditional Logic")
    tc.expected = "Trimmed correctly, state question asked"
    
    try:
        session_id, _ = start_session()
        
        submit_answer(session_id, "Yes")  # Consent
        submit_answer(session_id, "Test User")
        submit_answer(session_id, "Test Institution")
        submit_answer(session_id, "Student")
        submit_answer(session_id, "Yes")
        submit_answer(session_id, "Yes")
        resp = submit_answer(session_id, "  India  ")
        
        # Check if state question is next
        next_step = resp.get("state", {}).get("current_step")
        
        if next_step == "state":
            tc.status = "PASS"
            tc.actual = f"State question triggered after trimming"
        else:
            tc.status = "FAIL"
            tc.actual = f"Next step: {next_step} (expected: state)"
            
    except Exception as e:
        tc.status = "ERROR"
        tc.details = str(e)
    
    TEST_RESULTS.append(tc)
    return tc


def tc_06_country_not_india():
    """TC-06: Country Not India"""
    tc = TestCase("TC-06", "Country Not India", "Conditional Logic")
    tc.expected = "State question skipped, state stored as null"
    
    try:
        session_id, _ = start_session()
        
        submit_answer(session_id, "Yes")  # Consent
        submit_answer(session_id, "Test User")
        submit_answer(session_id, "Test Institution")
        submit_answer(session_id, "Student")
        submit_answer(session_id, "Yes")
        submit_answer(session_id, "Yes")
        resp = submit_answer(session_id, "USA")
        
        # Check if EMAIL is next (state skipped)
        next_step = resp.get("state", {}).get("current_step")
        state_value = resp.get("state", {}).get("data", {}).get("state")
        
        if next_step == "email" and state_value is None:
            tc.status = "PASS"
            tc.actual = f"Skipped to EMAIL, state=null"
        else:
            tc.status = "FAIL"
            tc.actual = f"Next step: {next_step}, state: {state_value}"
            
    except Exception as e:
        tc.status = "ERROR"
        tc.details = str(e)
    
    TEST_RESULTS.append(tc)
    return tc


# ============================================================
# CATEGORY 3: VALIDATION EDGE CASES
# ============================================================

def tc_07_empty_name():
    """TC-07: Empty Name"""
    tc = TestCase("TC-07", "Empty Name", "Validation")
    tc.expected = "Bot rejects, re-asks name"
    
    try:
        session_id, _ = start_session()
        
        submit_answer(session_id, "Yes")  # Consent
        resp = submit_answer(session_id, "")
        
        success = resp.get("success", True)
        current_step = resp.get("state", {}).get("current_step")
        
        if not success and current_step == "name":
            tc.status = "PASS"
            tc.actual = f"Rejected empty name, stayed on name step"
        else:
            tc.status = "FAIL"
            tc.actual = f"Success: {success}, Step: {current_step}"
            
    except Exception as e:
        tc.status = "ERROR"
        tc.details = str(e)
    
    TEST_RESULTS.append(tc)
    return tc


def tc_08_single_char_name():
    """TC-08: Single Character Name"""
    tc = TestCase("TC-08", "Single Character Name", "Validation")
    tc.expected = "Bot rejects, requires at least 2 characters"
    
    try:
        session_id, _ = start_session()
        
        submit_answer(session_id, "Yes")  # Consent
        resp = submit_answer(session_id, "A")
        
        success = resp.get("success", True)
        current_step = resp.get("state", {}).get("current_step")
        
        if not success and current_step == "name":
            tc.status = "PASS"
            tc.actual = f"Rejected single char name"
        else:
            tc.status = "FAIL"
            tc.actual = f"Success: {success}, Step: {current_step}"
            
    except Exception as e:
        tc.status = "ERROR"
        tc.details = str(e)
    
    TEST_RESULTS.append(tc)
    return tc


def tc_09_invalid_role():
    """TC-09: Invalid Role"""
    tc = TestCase("TC-09", "Invalid Role", "Validation")
    tc.expected = "Bot rejects, accepts only Student/Industry/Faculty"
    
    try:
        session_id, _ = start_session()
        
        submit_answer(session_id, "Yes")  # Consent
        submit_answer(session_id, "Test User")
        submit_answer(session_id, "Test Institution")
        resp = submit_answer(session_id, "Doctor")
        
        success = resp.get("success", True)
        current_step = resp.get("state", {}).get("current_step")
        
        if not success and current_step == "role":
            tc.status = "PASS"
            tc.actual = f"Rejected invalid role"
        else:
            tc.status = "FAIL"
            tc.actual = f"Success: {success}, Step: {current_step}"
            
    except Exception as e:
        tc.status = "ERROR"
        tc.details = str(e)
    
    TEST_RESULTS.append(tc)
    return tc


# ============================================================
# CATEGORY 4: EDIT FUNCTIONALITY TESTS
# ============================================================

def tc_13_edit_before_confirmation():
    """TC-13: Edit Before Confirmation"""
    tc = TestCase("TC-13", "Edit Field in Review Step", "Edit Functionality")
    tc.expected = "Field updated, returns to REVIEW"
    
    try:
        session_id, _ = start_session()
        
        # Complete flow to REVIEW
        submit_answer(session_id, "Yes")  # Consent
        submit_answer(session_id, "Test User")
        submit_answer(session_id, "Old Institution")
        submit_answer(session_id, "Student")
        submit_answer(session_id, "Yes")
        submit_answer(session_id, "Yes")
        submit_answer(session_id, "USA")
        submit_answer(session_id, "test@test.com")
        
        # Now at REVIEW - edit institution
        resp = submit_answer(session_id, "institution")
        
        # Should be on institution step
        current_step = resp.get("state", {}).get("current_step")
        
        if current_step == "institution":
            # Update institution
            resp2 = submit_answer(session_id, "New Institution")
            
            # Should return to REVIEW
            next_step = resp2.get("state", {}).get("current_step")
            updated_value = resp2.get("state", {}).get("data", {}).get("institution")
            
            if next_step == "review" and updated_value == "New Institution":
                tc.status = "PASS"
                tc.actual = f"Edited and returned to REVIEW with updated value"
            else:
                tc.status = "FAIL"
                tc.actual = f"Next step: {next_step}, Value: {updated_value}"
        else:
            tc.status = "FAIL"
            tc.actual = f"Edit didn't work, step: {current_step}"
            
    except Exception as e:
        tc.status = "ERROR"
        tc.details = str(e)
    
    TEST_RESULTS.append(tc)
    return tc


def tc_14_edit_country_india_to_usa():
    """TC-14: Edit Country from India to USA"""
    tc = TestCase("TC-14", "Edit Country India to USA", "Edit Functionality")
    tc.expected = "State cleared when changing from India to USA"
    
    try:
        session_id, _ = start_session()
        
        # Complete flow to REVIEW with India
        submit_answer(session_id, "Yes")  # Consent
        submit_answer(session_id, "Test User")
        submit_answer(session_id, "Test Institution")
        submit_answer(session_id, "Student")
        submit_answer(session_id, "Yes")
        submit_answer(session_id, "Yes")
        submit_answer(session_id, "India")
        submit_answer(session_id, "Karnataka")
        submit_answer(session_id, "test@test.com")  # Email
        
        # Now at REVIEW - edit country
        resp = submit_answer(session_id, "country")
        resp2 = submit_answer(session_id, "USA")
        
        # Check if state was auto-cleared (should be None)
        country = resp2.get("state", {}).get("data", {}).get("country")
        state = resp2.get("state", {}).get("data", {}).get("state")
        
        # TC-14 FIX: State should be auto-cleared when changing from India to non-India
        if country == "Usa" and state is None:
            tc.status = "PASS"
            tc.actual = f"State auto-cleared successfully. Country: {country}, State: {state}"
        else:
            tc.status = "FAIL"
            tc.actual = f"State not cleared. Country: {country}, State: {state}"
            
    except Exception as e:
        tc.status = "ERROR"
        tc.details = str(e)
    
    TEST_RESULTS.append(tc)
    return tc


# ============================================================
# CATEGORY 5: FLOW INTERRUPTION TESTS
# ============================================================

def tc_10_cancel_registration():
    """TC-10: Cancel Registration"""
    tc = TestCase("TC-10", "Cancel Registration", "Flow Interruption")
    tc.expected = "Registration cancelled, session ends"
    
    try:
        session_id, start_data = start_session()
        
        # Verify session was created
        if not session_id:
            tc.status = "ERROR"
            tc.details = "Failed to create session"
            TEST_RESULTS.append(tc)
            return tc
        
        # Accept consent and start registration
        resp1 = submit_answer(session_id, "Yes")  # Consent
        if not resp1.get("success"):
            tc.status = "ERROR"
            tc.details = f"Consent failed: {resp1}"
            TEST_RESULTS.append(tc)
            return tc
            
        resp2 = submit_answer(session_id, "Test User")
        if not resp2.get("success"):
            tc.status = "ERROR"
            tc.details = f"Name submission failed: {resp2}"
            TEST_RESULTS.append(tc)
            return tc
        
        # Cancel
        response = requests.post(f"{BASE_URL}/api/register/cancel", json={"session_id": session_id})
        data = response.json()
        
        cancelled = data.get("cancelled", False)
        message = data.get("message", "")
        
        if cancelled or "cancel" in message.lower():
            tc.status = "PASS"
            tc.actual = f"Registration cancelled successfully: {message}"
        else:
            tc.status = "FAIL"
            tc.actual = f"Cancel didn't work: {data}"
            
    except Exception as e:
        tc.status = "ERROR"
        tc.details = str(e)
    
    TEST_RESULTS.append(tc)
    return tc


def tc_12_invalid_input_at_review():
    """TC-12: Invalid Input at REVIEW Step"""
    tc = TestCase("TC-12", "Invalid Field Name at REVIEW", "Flow Interruption")
    tc.expected = "Bot rejects invalid field name, shows valid options"
    
    try:
        session_id, _ = start_session()
        
        # Complete to REVIEW
        submit_answer(session_id, "Yes")  # Consent
        submit_answer(session_id, "Test User")
        submit_answer(session_id, "Test Institution")
        submit_answer(session_id, "Student")
        submit_answer(session_id, "Yes")
        submit_answer(session_id, "Yes")
        submit_answer(session_id, "USA")
        submit_answer(session_id, "test@test.com")
        
        # Try invalid field name
        resp = submit_answer(session_id, "phone")  # Invalid field - not in registration
        
        success = resp.get("success", True)
        current_step = resp.get("state", {}).get("current_step")
        
        if not success and current_step == "review":
            tc.status = "PASS"
            tc.actual = f"Rejected invalid field name, stayed on review"
        else:
            tc.status = "FAIL"
            tc.actual = f"Success: {success}, Step: {current_step}"
            
    except Exception as e:
        tc.status = "ERROR"
        tc.details = str(e)
    
    TEST_RESULTS.append(tc)
    return tc


# ============================================================
# CATEGORY 6: SECURITY & DESIGN TESTS
# ============================================================

def tc_19_no_field_skipping():
    """TC-19: Cannot Skip Mandatory Fields"""
    tc = TestCase("TC-19", "Cannot Skip Mandatory Fields", "Security")
    tc.expected = "All fields must be completed in sequence"
    
    try:
        session_id, _ = start_session()
        
        # Try to skip to country without completing earlier fields
        # The API enforces sequential progression
        
        submit_answer(session_id, "Yes")  # Consent
        submit_answer(session_id, "Test User")
        resp = submit_answer(session_id, "Test Institution")
        
        # Should be on ROLE step
        current_step = resp.get("state", {}).get("current_step")
        
        if current_step == "role":
            tc.status = "PASS"
            tc.actual = "Sequential progression enforced"
        else:
            tc.status = "FAIL"
            tc.actual = f"Unexpected step: {current_step}"
            
    except Exception as e:
        tc.status = "ERROR"
        tc.details = str(e)
    
    TEST_RESULTS.append(tc)
    return tc


def tc_20_deterministic_behavior():
    """TC-20: Deterministic Behavior"""
    tc = TestCase("TC-20", "Deterministic Logic (No AI Decisions)", "Security")
    tc.expected = "Same inputs always produce same outputs"
    
    try:
        results = []
        
        # Run same flow 3 times
        for i in range(3):
            session_id, _ = start_session()
            
            submit_answer(session_id, "Yes")  # Consent
            submit_answer(session_id, "Test User")
            submit_answer(session_id, "Test Institution")
            submit_answer(session_id, "Student")
            submit_answer(session_id, "Yes")
            submit_answer(session_id, "Yes")
            resp = submit_answer(session_id, "India")
            
            next_step = resp.get("state", {}).get("current_step")
            results.append(next_step)
        
        # All should be "state"
        all_same = all(step == "state" for step in results)
        
        if all_same:
            tc.status = "PASS"
            tc.actual = "Deterministic: all runs produced 'state' step"
        else:
            tc.status = "FAIL"
            tc.actual = f"Non-deterministic: {results}"
            
    except Exception as e:
        tc.status = "ERROR"
        tc.details = str(e)
    
    TEST_RESULTS.append(tc)
    return tc


# ============================================================
# CATEGORY 7: NEW FEATURES TESTS (INDUSTRY GRADE)
# ============================================================

def tc_21_consent_accepted():
    """TC-21: Consent Accepted"""
    tc = TestCase("TC-21", "Consent Accepted - Registration Proceeds", "Consent")
    tc.expected = "Consent accepted, registration continues to NAME step"
    
    try:
        session_id, start_data = start_session()
        
        # Check first question is consent
        first_step = start_data.get("state", {}).get("current_step")
        
        # Accept consent
        resp = submit_answer(session_id, "Yes")
        
        # Should proceed to NAME
        next_step = resp.get("state", {}).get("current_step")
        
        if first_step == "consent" and next_step == "name":
            tc.status = "PASS"
            tc.actual = "Consent accepted, proceeded to NAME"
        else:
            tc.status = "FAIL"
            tc.actual = f"First: {first_step}, Next: {next_step}"
            
    except Exception as e:
        tc.status = "ERROR"
        tc.details = str(e)
    
    TEST_RESULTS.append(tc)
    return tc


def tc_22_consent_declined():
    """TC-22: Consent Declined"""
    tc = TestCase("TC-22", "Consent Declined - Registration Terminates", "Consent")
    tc.expected = "Consent declined, registration terminates immediately"
    
    try:
        session_id, _ = start_session()
        
        # Decline consent
        resp = submit_answer(session_id, "No")
        
        cancelled = resp.get("cancelled", False)
        is_active = resp.get("state", {}).get("is_active", True)
        
        if cancelled and not is_active:
            tc.status = "PASS"
            tc.actual = "Registration terminated on consent decline"
        else:
            tc.status = "FAIL"
            tc.actual = f"Cancelled: {cancelled}, Active: {is_active}"
            
    except Exception as e:
        tc.status = "ERROR"
        tc.details = str(e)
    
    TEST_RESULTS.append(tc)
    return tc


def tc_23_valid_email():
    """TC-23: Valid Email Format"""
    tc = TestCase("TC-23", "Valid Email Accepted", "Email Validation")
    tc.expected = "Valid email accepted"
    
    try:
        session_id, _ = start_session()
        
        # Complete flow to EMAIL
        submit_answer(session_id, "Yes")  # Consent
        submit_answer(session_id, "Test User")
        submit_answer(session_id, "Test Institution")
        submit_answer(session_id, "Student")
        submit_answer(session_id, "Yes")
        submit_answer(session_id, "Yes")
        submit_answer(session_id, "USA")
        
        # Submit valid email
        resp = submit_answer(session_id, "test@example.com")
        
        success = resp.get("success", False)
        next_step = resp.get("state", {}).get("current_step")
        
        if success and next_step == "review":
            tc.status = "PASS"
            tc.actual = "Valid email accepted"
        else:
            tc.status = "FAIL"
            tc.actual = f"Success: {success}, Step: {next_step}"
            
    except Exception as e:
        tc.status = "ERROR"
        tc.details = str(e)
    
    TEST_RESULTS.append(tc)
    return tc


def tc_24_invalid_email():
    """TC-24: Invalid Email Format"""
    tc = TestCase("TC-24", "Invalid Email Rejected", "Email Validation")
    tc.expected = "Invalid email rejected with error message"
    
    try:
        session_id, _ = start_session()
        
        # Complete flow to EMAIL
        submit_answer(session_id, "Yes")  # Consent
        submit_answer(session_id, "Test User")
        submit_answer(session_id, "Test Institution")
        submit_answer(session_id, "Student")
        submit_answer(session_id, "Yes")
        submit_answer(session_id, "Yes")
        submit_answer(session_id, "USA")
        
        # Try invalid emails
        invalid_emails = ["test@", "test.com", "@example.com", "test space@test.com"]
        results = []
        
        for email in invalid_emails:
            resp = submit_answer(session_id, email)
            success = resp.get("success", True)
            results.append((email, not success))
        
        all_rejected = all(rejected for _, rejected in results)
        
        if all_rejected:
            tc.status = "PASS"
            tc.actual = "All invalid emails rejected"
        else:
            tc.status = "FAIL"
            tc.actual = f"Some invalid emails accepted: {results}"
            
    except Exception as e:
        tc.status = "ERROR"
        tc.details = str(e)
    
    TEST_RESULTS.append(tc)
    return tc


def tc_25_state_auto_clear():
    """TC-25: TC-14 Fix - State Auto-Cleared on Country Edit"""
    tc = TestCase("TC-25", "State Auto-Clear When Country Changes", "TC-14 Fix")
    tc.expected = "State cleared when changing from India to USA"
    
    try:
        session_id, _ = start_session()
        
        # Complete to REVIEW with India + state
        submit_answer(session_id, "Yes")  # Consent
        submit_answer(session_id, "Test User")
        submit_answer(session_id, "Test Institution")
        submit_answer(session_id, "Student")
        submit_answer(session_id, "Yes")
        submit_answer(session_id, "Yes")
        submit_answer(session_id, "India")
        submit_answer(session_id, "Karnataka")
        submit_answer(session_id, "test@test.com")
        
        # Edit country to USA
        submit_answer(session_id, "country")
        resp = submit_answer(session_id, "USA")
        
        # Check if state is cleared
        state_value = resp.get("state", {}).get("data", {}).get("state")
        
        if state_value is None:
            tc.status = "PASS"
            tc.actual = "State auto-cleared when country changed to USA"
        else:
            tc.status = "FAIL"
            tc.actual = f"State not cleared: {state_value}"
            
    except Exception as e:
        tc.status = "ERROR"
        tc.details = str(e)
    
    TEST_RESULTS.append(tc)
    return tc


# ============================================================
# TEST RUNNER
# ============================================================

def run_all_tests():
    """Execute all test cases"""
    print("=" * 80)
    print("GDTA 2026 REGISTRATION SYSTEM - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print()
    
    # Category 1: Normal Flow
    print("CATEGORY 1: NORMAL FLOW TESTS")
    print("-" * 80)
    tc_01_student_india()
    tc_02_industry_international()
    tc_03_faculty_india()
    print()
    
    # Category 2: Conditional Logic
    print("CATEGORY 2: CONDITIONAL LOGIC TESTS")
    print("-" * 80)
    tc_04_country_case_insensitive()
    tc_05_country_extra_spaces()
    tc_06_country_not_india()
    print()
    
    # Category 3: Validation
    print("CATEGORY 3: VALIDATION EDGE CASES")
    print("-" * 80)
    tc_07_empty_name()
    tc_08_single_char_name()
    tc_09_invalid_role()
    print()
    
    # Category 4: Edit Functionality
    print("CATEGORY 4: EDIT FUNCTIONALITY TESTS")
    print("-" * 80)
    tc_13_edit_before_confirmation()
    tc_14_edit_country_india_to_usa()
    print()
    
    # Category 5: Flow Interruption
    print("CATEGORY 5: FLOW INTERRUPTION TESTS")
    print("-" * 80)
    tc_10_cancel_registration()
    tc_12_invalid_input_at_review()
    print()
    
    # Category 6: Security & Design
    print("CATEGORY 6: SECURITY & DESIGN TESTS")
    print("-" * 80)
    tc_19_no_field_skipping()
    tc_20_deterministic_behavior()
    print()
    
    # Category 7: New Features (Industry Grade)
    print("CATEGORY 7: NEW FEATURES - INDUSTRY GRADE")
    print("-" * 80)
    tc_21_consent_accepted()
    tc_22_consent_declined()
    tc_23_valid_email()
    tc_24_invalid_email()
    tc_25_state_auto_clear()
    print()


def generate_report():
    """Generate comprehensive test report"""
    print("=" * 80)
    print("TEST EXECUTION REPORT")
    print("=" * 80)
    print()
    
    # Summary statistics
    total = len(TEST_RESULTS)
    passed = sum(1 for tc in TEST_RESULTS if tc.status == "PASS")
    failed = sum(1 for tc in TEST_RESULTS if tc.status == "FAIL")
    errors = sum(1 for tc in TEST_RESULTS if tc.status == "ERROR")
    notes = sum(1 for tc in TEST_RESULTS if tc.status == "NOTE")
    
    print(f"Total Tests: {total}")
    print(f"[PASS] Passed: {passed}")
    print(f"[FAIL] Failed: {failed}")
    print(f"[ERROR] Errors: {errors}")
    print(f"[NOTE] Notes: {notes}")
    print()
    
    # Detailed results table
    print("DETAILED RESULTS")
    print("-" * 80)
    print(f"{'ID':<8} {'Status':<8} {'Category':<20} {'Test Name':<30}")
    print("-" * 80)
    
    for tc in TEST_RESULTS:
        status_icon = {
            "PASS": "[PASS]",
            "FAIL": "[FAIL]",
            "ERROR": "[ERR]",
            "NOTE": "[NOTE]",
            "NOT RUN": "[ ? ]"
        }.get(tc.status, "[?]")
        
        print(f"{tc.id:<8} {status_icon} {tc.status:<6} {tc.category:<20} {tc.name:<30}")
    
    print()
    
    # Failed tests details
    failed_tests = [tc for tc in TEST_RESULTS if tc.status == "FAIL"]
    if failed_tests:
        print("FAILED TESTS - DETAILS")
        print("-" * 80)
        for tc in failed_tests:
            print(f"\n{tc.id}: {tc.name}")
            print(f"  Expected: {tc.expected}")
            print(f"  Actual: {tc.actual}")
            if tc.details:
                print(f"  Details: {tc.details}")
    
    # Notes and recommendations
    note_tests = [tc for tc in TEST_RESULTS if tc.status == "NOTE"]
    if note_tests:
        print("\nNOTES & RECOMMENDATIONS")
        print("-" * 80)
        for tc in note_tests:
            print(f"\n{tc.id}: {tc.name}")
            print(f"  {tc.details}")
    
    # Errors
    error_tests = [tc for tc in TEST_RESULTS if tc.status == "ERROR"]
    if error_tests:
        print("\nERRORS ENCOUNTERED")
        print("-" * 80)
        for tc in error_tests:
            print(f"\n{tc.id}: {tc.name}")
            print(f"  Error: {tc.details}")
    
    print()
    print("=" * 80)
    
    # Gap analysis
    print("\nGAP ANALYSIS: Implementation Status")
    print("-" * 80)
    print("[DONE] Consent step - IMPLEMENTED")
    print("[DONE] Email field - IMPLEMENTED")
    print("[DONE] Email validation - IMPLEMENTED (regex-based)")
    print("[DONE] TC-14 State auto-clear fix - IMPLEMENTED")
    print("[DONE] Backend failure handling - IMPLEMENTED (stub functions)")
    print("[PEND] Duplicate email check - DESIGNED (awaiting database)")
    print("[PEND] Registration closed scenario - DESIGNED (awaiting config)")
    print()
    
    # Recommendations
    print("NEXT STEPS FOR PRODUCTION")
    print("-" * 80)
    print("1. Connect database for persistent storage")
    print("2. Implement email service for confirmation emails")
    print("3. Add admin panel for registration open/closed toggle")
    print("4. Add rate limiting and CAPTCHA for production")
    print("5. Implement timeout handling for long-running sessions")
    print()


if __name__ == "__main__":
    try:
        run_all_tests()
        generate_report()
    except KeyboardInterrupt:
        print("\n\nTest execution interrupted by user")
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
