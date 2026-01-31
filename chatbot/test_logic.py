"""
Test script to verify the scheduling logic works correctly
Run this before starting the server to ensure everything is working
"""

import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logic.planner import build_schedule
from logic.clash_detector import validate_schedule


def load_sessions():
    """Load sessions data"""
    with open('data/sessions.json', 'r') as f:
        return json.load(f)


def test_student_schedule():
    """Test building a student schedule"""
    print("=" * 60)
    print("TEST 1: Building Student Schedule")
    print("=" * 60)
    
    sessions_data = load_sessions()
    preferences = {
        'interest': 'student',
        'days': 2
    }
    
    schedule = build_schedule(sessions_data, preferences)
    
    print(f"✓ Total sessions selected: {schedule['metadata']['total_sessions']}")
    print(f"✓ Clashes resolved: {schedule['metadata']['clashes_resolved']}")
    print(f"✓ Schedule valid: {schedule['metadata']['validation']['is_valid']}")
    
    if not schedule['metadata']['validation']['is_valid']:
        print("✗ ERRORS FOUND:")
        for error in schedule['metadata']['validation']['errors']:
            print(f"  - {error}")
        return False
    
    print("\nDay 1 Sessions:")
    for session in schedule['day1']:
        print(f"  {session['start']}-{session['end']}: {session['title']}")
    
    print("\nDay 2 Sessions:")
    for session in schedule['day2']:
        print(f"  {session['start']}-{session['end']}: {session['title']}")
    
    print("\n✓ Student schedule test PASSED\n")
    return True


def test_industry_schedule():
    """Test building an industry schedule"""
    print("=" * 60)
    print("TEST 2: Building Industry Schedule")
    print("=" * 60)
    
    sessions_data = load_sessions()
    preferences = {
        'interest': 'industry',
        'days': 2
    }
    
    schedule = build_schedule(sessions_data, preferences)
    
    print(f"✓ Total sessions selected: {schedule['metadata']['total_sessions']}")
    print(f"✓ Clashes resolved: {schedule['metadata']['clashes_resolved']}")
    print(f"✓ Schedule valid: {schedule['metadata']['validation']['is_valid']}")
    
    if not schedule['metadata']['validation']['is_valid']:
        print("✗ ERRORS FOUND:")
        for error in schedule['metadata']['validation']['errors']:
            print(f"  - {error}")
        return False
    
    print("\n✓ Industry schedule test PASSED\n")
    return True


def test_parallel_sessions():
    """Test that parallel session detection works"""
    print("=" * 60)
    print("TEST 3: Parallel Session Detection")
    print("=" * 60)
    
    sessions_data = load_sessions()
    all_sessions = sessions_data['sessions']
    
    # Find sessions at 10:30 on day 1
    parallel = [s for s in all_sessions 
                if s['day'] == 1 and s['start'] == '10:30' and s['type'] != 'break']
    
    print(f"✓ Found {len(parallel)} parallel sessions at 10:30 on Day 1:")
    for session in parallel:
        print(f"  - {session['title']} ({', '.join(session['tags'])})")
    
    if len(parallel) < 2:
        print("✗ Expected at least 2 parallel sessions")
        return False
    
    print("\n✓ Parallel session test PASSED\n")
    return True


def test_no_breaks_in_schedule():
    """Test that breaks are excluded from final schedule"""
    print("=" * 60)
    print("TEST 4: Breaks Exclusion")
    print("=" * 60)
    
    sessions_data = load_sessions()
    preferences = {'interest': 'student', 'days': 2}
    schedule = build_schedule(sessions_data, preferences)
    
    all_scheduled = schedule['day1'] + schedule['day2']
    breaks = [s for s in all_scheduled if s['type'] == 'break']
    
    if breaks:
        print(f"✗ Found {len(breaks)} breaks in schedule (should be 0)")
        return False
    
    print("✓ No breaks found in schedule")
    print("✓ Breaks exclusion test PASSED\n")
    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("GDTA 2026 CHATBOT BACKEND - LOGIC TESTS")
    print("=" * 60 + "\n")
    
    tests = [
        test_student_schedule,
        test_industry_schedule,
        test_parallel_sessions,
        test_no_breaks_in_schedule
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ TEST FAILED WITH ERROR: {e}\n")
            results.append(False)
    
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Passed: {sum(results)}/{len(results)}")
    print(f"Failed: {len(results) - sum(results)}/{len(results)}")
    
    if all(results):
        print("\n🎉 ALL TESTS PASSED! System is ready to run.")
        print("\nStart the server with: python app.py")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED. Fix errors before running server.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
