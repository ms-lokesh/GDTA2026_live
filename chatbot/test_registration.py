"""
Test Registration Flow - Verify deterministic registration logic
Run this to test the registration system before using the API
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logic.registration import (
    start_registration,
    get_current_question,
    process_input,
    get_summary,
    validate_input,
    RegistrationSteps
)


def test_registration_flow_india():
    """Test complete registration flow for India (includes state question)"""
    print("=" * 60)
    print("TEST 1: Registration Flow - India (with state)")
    print("=" * 60)
    
    reg_state = start_registration()
    
    # Step 1: GDTA Affiliation
    print("\n1. GDTA Affiliation")
    question = get_current_question(reg_state)
    print(f"Question: {question['question']}")
    print(f"Options: {question['options']}")
    
    result = process_input(reg_state, "Yes")
    print(f"Answer: Yes")
    print(f"Status: {result['success']}")
    print(f"Response: {result['message']}")
    
    # Step 2: Country
    print("\n2. Country")
    question = get_current_question(reg_state)
    print(f"Question: {question['question']}")
    
    result = process_input(reg_state, "India")
    print(f"Answer: India")
    print(f"Status: {result['success']}")
    print(f"Response: {result['message']}")
    
    # Step 3: State (should be asked for India)
    print("\n3. State (conditional)")
    question = get_current_question(reg_state)
    print(f"Question: {question['question']}")
    print(f"Current step: {reg_state.current_step}")
    
    if reg_state.current_step == RegistrationSteps.STATE:
        print("✓ State question triggered correctly for India")
        result = process_input(reg_state, "Maharashtra")
        print(f"Answer: Maharashtra")
        print(f"Status: {result['success']}")
        print(f"Response: {result['message']}")
    else:
        print("✗ ERROR: State question should be asked for India")
        return False
    
    # Step 4: Confirmation
    print("\n4. Confirmation")
    question = get_current_question(reg_state)
    print(f"Question: {question['question']}")
    summary = get_summary(reg_state)
    print(f"Summary:\\n{summary}")
    
    result = process_input(reg_state, "CONFIRM")
    print(f"Answer: CONFIRM")
    print(f"Status: {result['success']}")
    print(f"Completed: {result['completed']}")
    print(f"Response: {result['message']}")
    
    # Verify data
    print("\n✓ Final Data:")
    print(f"  GDTA Affiliation: {reg_state.data['gdta_affiliation']}")
    print(f"  Country: {reg_state.data['country']}")
    print(f"  State: {reg_state.data['state']}")
    
    if reg_state.data['state'] == 'Maharashtra':
        print("\n✓ Test PASSED: India registration flow works correctly\n")
        return True
    else:
        print("\n✗ Test FAILED: State not captured correctly\n")
        return False


def test_registration_flow_non_india():
    """Test registration flow for non-India country (skips state)"""
    print("=" * 60)
    print("TEST 2: Registration Flow - USA (no state)")
    print("=" * 60)
    
    reg_state = start_registration()
    
    # Step 1: GDTA Affiliation
    result = process_input(reg_state, "No")
    print(f"1. GDTA Affiliation: No - {result['success']}")
    
    # Step 2: Country
    result = process_input(reg_state, "USA")
    print(f"2. Country: USA - {result['success']}")
    
    # Step 3: Should skip to confirmation
    print(f"\n3. Current step: {reg_state.current_step}")
    
    if reg_state.current_step == RegistrationSteps.CONFIRMATION:
        print("✓ State question correctly skipped for non-India country")
    else:
        print(f"✗ ERROR: Expected confirmation step, got {reg_state.current_step}")
        return False
    
    # Confirm
    result = process_input(reg_state, "CONFIRM")
    print(f"4. Confirmation: CONFIRM - {result['completed']}")
    
    # Verify data
    print("\n✓ Final Data:")
    print(f"  GDTA Affiliation: {reg_state.data['gdta_affiliation']}")
    print(f"  Country: {reg_state.data['country']}")
    print(f"  State: {reg_state.data['state']}")
    
    if reg_state.data['state'] is None:
        print("\n✓ Test PASSED: State correctly set to null for non-India\n")
        return True
    else:
        print("\n✗ Test FAILED: State should be null\n")
        return False


def test_validation():
    """Test input validation rules"""
    print("=" * 60)
    print("TEST 3: Input Validation")
    print("=" * 60)
    
    # Test GDTA affiliation validation
    print("\n1. GDTA Affiliation Validation")
    valid, value, error = validate_input("yes", RegistrationSteps.GDTA_AFFILIATION)
    print(f"  'yes' -> Valid: {valid}, Normalized: {value}")
    assert valid and value == "Yes"
    
    valid, value, error = validate_input("Not sure", RegistrationSteps.GDTA_AFFILIATION)
    print(f"  'Not sure' -> Valid: {valid}, Normalized: {value}")
    assert valid and value == "Not sure"
    
    valid, value, error = validate_input("maybe", RegistrationSteps.GDTA_AFFILIATION)
    print(f"  'maybe' -> Valid: {valid}, Error: {error}")
    assert not valid
    
    # Test country validation
    print("\n2. Country Validation")
    valid, value, error = validate_input("india", RegistrationSteps.COUNTRY)
    print(f"  'india' -> Valid: {valid}, Normalized: {value}")
    assert valid and value == "India"
    
    valid, value, error = validate_input("", RegistrationSteps.COUNTRY)
    print(f"  '' -> Valid: {valid}, Error: {error}")
    assert not valid
    
    # Test confirmation validation
    print("\n3. Confirmation Validation")
    valid, value, error = validate_input("confirm", RegistrationSteps.CONFIRMATION)
    print(f"  'confirm' -> Valid: {valid}, Normalized: {value}")
    assert valid and value == "CONFIRM"
    
    valid, value, error = validate_input("edit", RegistrationSteps.CONFIRMATION)
    print(f"  'edit' -> Valid: {valid}, Normalized: {value}")
    assert valid and value == "EDIT"
    
    print("\n✓ Test PASSED: All validation rules work correctly\n")
    return True


def test_edit_flow():
    """Test EDIT flow at confirmation"""
    print("=" * 60)
    print("TEST 4: EDIT Flow")
    print("=" * 60)
    
    reg_state = start_registration()
    
    # Fill in data
    process_input(reg_state, "Yes")
    process_input(reg_state, "Canada")
    
    print(f"Before EDIT: Step = {reg_state.current_step}")
    print(f"Data: {reg_state.data}")
    
    # Choose EDIT at confirmation
    result = process_input(reg_state, "EDIT")
    
    print(f"\nAfter EDIT: Step = {reg_state.current_step}")
    print(f"Data reset: {reg_state.data}")
    
    if reg_state.current_step == RegistrationSteps.GDTA_AFFILIATION:
        print("\n✓ Test PASSED: EDIT correctly restarts from beginning\n")
        return True
    else:
        print("\n✗ Test FAILED: Should restart from GDTA affiliation\n")
        return False


def test_case_insensitive():
    """Test case insensitive matching"""
    print("=" * 60)
    print("TEST 5: Case Insensitive Matching")
    print("=" * 60)
    
    reg_state = start_registration()
    
    # Test various cases for India
    test_cases = [
        ("INDIA", True),
        ("india", True),
        ("India", True),
        ("InDiA", True),
        ("United States", False)
    ]
    
    for country_input, should_ask_state in test_cases:
        reg_state = start_registration()
        process_input(reg_state, "Yes")
        process_input(reg_state, country_input)
        
        is_state_step = reg_state.current_step == RegistrationSteps.STATE
        
        print(f"  Country: '{country_input}' -> Asks state: {is_state_step} (expected: {should_ask_state})")
        
        if is_state_step != should_ask_state:
            print(f"\\n✗ Test FAILED for '{country_input}'\\n")
            return False
    
    print("\n✓ Test PASSED: Case insensitive matching works correctly\n")
    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("GDTA 2026 - REGISTRATION LOGIC TESTS")
    print("=" * 60 + "\n")
    
    tests = [
        test_registration_flow_india,
        test_registration_flow_non_india,
        test_validation,
        test_edit_flow,
        test_case_insensitive
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ TEST FAILED WITH ERROR: {e}\n")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Passed: {sum(results)}/{len(results)}")
    print(f"Failed: {len(results) - sum(results)}/{len(results)}")
    
    if all(results):
        print("\n🎉 ALL TESTS PASSED! Registration system is ready.")
        print("\nKey features verified:")
        print("  ✓ Deterministic step-based flow")
        print("  ✓ Conditional state question (India only)")
        print("  ✓ Input validation and normalization")
        print("  ✓ EDIT flow to restart registration")
        print("  ✓ Case insensitive country matching")
        print("\nStart the server and test with: /api/chat")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED. Fix errors before using API.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
