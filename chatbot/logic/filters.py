"""
Filters - Deterministic filtering logic for sessions
This module contains all filtering rules - NO AI DECISIONS
"""


def filter_by_tags(sessions, required_tags):
    """
    Filter sessions that contain ALL required tags
    
    Args:
        sessions: List of session dicts
        required_tags: List of tags that must be present (e.g., ['student'])
    
    Returns:
        Filtered list of sessions
    """
    if not required_tags:
        return sessions
    
    filtered = []
    for session in sessions:
        session_tags = session.get('tags', [])
        # Check if all required tags are in the session's tags
        if all(tag in session_tags for tag in required_tags):
            filtered.append(session)
    
    return filtered


def filter_by_any_tag(sessions, tags):
    """
    Filter sessions that contain ANY of the provided tags
    
    Args:
        sessions: List of session dicts
        tags: List of tags (e.g., ['student', 'industry'])
    
    Returns:
        Filtered list of sessions
    """
    if not tags:
        return sessions
    
    filtered = []
    for session in sessions:
        session_tags = session.get('tags', [])
        # Check if any tag matches
        if any(tag in session_tags for tag in tags):
            filtered.append(session)
    
    return filtered


def filter_by_day(sessions, day):
    """
    Filter sessions for a specific day
    
    Args:
        sessions: List of session dicts
        day: Integer day number (1 or 2)
    
    Returns:
        Sessions for that day only
    """
    return [s for s in sessions if s.get('day') == day]


def filter_by_type(sessions, session_types):
    """
    Filter sessions by type(s)
    
    Args:
        sessions: List of session dicts
        session_types: List of types (e.g., ['workshop', 'talk'])
    
    Returns:
        Sessions matching any of the types
    """
    if not session_types:
        return sessions
    
    return [s for s in sessions if s.get('type') in session_types]


def exclude_breaks(sessions):
    """
    Remove all break sessions (coffee, lunch, etc.)
    
    LOGIC: Breaks are automatically excluded from schedules
    User doesn't need to select breaks manually
    """
    return [s for s in sessions if s.get('type') != 'break']


def get_mandatory_sessions(sessions):
    """
    Get sessions that should be included for everyone
    
    LOGIC: Keynotes and closing sessions are usually for all attendees
    """
    return [s for s in sessions if s.get('type') in ['keynote']]


def sort_sessions_by_time(sessions):
    """
    Sort sessions chronologically (day, then start time)
    
    Returns:
        Sorted list of sessions
    """
    from logic.clash_detector import time_to_minutes
    
    def sort_key(session):
        day = session.get('day', 0)
        start = session.get('start', '00:00')
        return (day, time_to_minutes(start))
    
    return sorted(sessions, key=sort_key)


def filter_by_interest(sessions, interest):
    """
    Main filtering function based on user interest
    
    Args:
        sessions: All sessions
        interest: 'student' or 'industry'
    
    Returns:
        Filtered sessions appropriate for the user
    
    LOGIC:
    - Include all mandatory sessions (keynotes)
    - Include sessions tagged with user's interest
    - Exclude breaks automatically
    """
    # Step 1: Remove breaks
    no_breaks = exclude_breaks(sessions)
    
    # Step 2: Get mandatory sessions
    mandatory = get_mandatory_sessions(no_breaks)
    
    # Step 3: Get interest-specific sessions
    if interest:
        interest_sessions = filter_by_tags(no_breaks, [interest])
    else:
        interest_sessions = no_breaks
    
    # Step 4: Combine and deduplicate
    combined = mandatory + interest_sessions
    unique_sessions = list({s['id']: s for s in combined}.values())
    
    # Step 5: Sort by time
    return sort_sessions_by_time(unique_sessions)
