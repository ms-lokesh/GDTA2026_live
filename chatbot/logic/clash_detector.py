"""
Clash Detector - Deterministic logic for detecting session overlaps
This module ensures only ONE session can be selected per time slot
"""

from datetime import datetime, timedelta


def time_to_minutes(time_str):
    """Convert HH:MM string to minutes since midnight"""
    hours, minutes = map(int, time_str.split(':'))
    return hours * 60 + minutes


def sessions_overlap(session1, session2):
    """
    Check if two sessions overlap in time
    Returns True if they clash, False otherwise
    
    LOGIC: Sessions clash if they occur on the same day and their time ranges overlap
    """
    # Different days = no clash
    if session1['day'] != session2['day']:
        return False
    
    # Convert times to minutes for easier comparison
    s1_start = time_to_minutes(session1['start'])
    s1_end = time_to_minutes(session1['end'])
    s2_start = time_to_minutes(session2['start'])
    s2_end = time_to_minutes(session2['end'])
    
    # Check for overlap: sessions overlap if one starts before the other ends
    # and the other starts before the first ends
    return s1_start < s2_end and s2_start < s1_end


def find_clashes(selected_sessions, candidate_session):
    """
    Find all sessions in selected_sessions that clash with candidate_session
    Returns list of clashing sessions
    """
    clashes = []
    for session in selected_sessions:
        if sessions_overlap(session, candidate_session):
            clashes.append(session)
    return clashes


def has_any_clash(selected_sessions, candidate_session):
    """
    Quick check: does candidate_session clash with ANY selected session?
    Returns True if there's at least one clash
    """
    return len(find_clashes(selected_sessions, candidate_session)) > 0


def remove_clashing_sessions(sessions_list):
    """
    Given a list of sessions, remove sessions that clash with each other
    Priority: Keep the session that appears first in the list
    
    This is used when the backend needs to clean up a session list
    """
    cleaned = []
    
    for candidate in sessions_list:
        if not has_any_clash(cleaned, candidate):
            cleaned.append(candidate)
    
    return cleaned


def get_time_slots(sessions):
    """
    Group sessions by time slots (same day + overlapping times)
    Returns a dict: {slot_key: [sessions in that slot]}
    
    This helps identify all parallel sessions
    """
    slots = {}
    
    for session in sessions:
        # Skip breaks
        if session.get('type') == 'break':
            continue
            
        slot_key = f"day{session['day']}_{session['start']}_{session['end']}"
        
        if slot_key not in slots:
            slots[slot_key] = []
        slots[slot_key].append(session)
    
    return slots


def validate_schedule(schedule):
    """
    Validate that a schedule has no clashes
    Returns (is_valid, list_of_errors)
    
    IMPORTANT: This is the final check before returning a schedule to the user
    """
    errors = []
    all_sessions = []
    
    # Collect all sessions from all days
    for day_key, sessions in schedule.items():
        all_sessions.extend(sessions)
    
    # Check each pair of sessions
    for i, session1 in enumerate(all_sessions):
        for session2 in all_sessions[i+1:]:
            if sessions_overlap(session1, session2):
                error = f"CLASH: '{session1['title']}' overlaps with '{session2['title']}' on day {session1['day']}"
                errors.append(error)
    
    return len(errors) == 0, errors
