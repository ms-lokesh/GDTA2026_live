"""
Planner - Deterministic schedule planning logic
This is the CORE LOGIC ENGINE - makes all decisions about schedule building

NO AI INVOLVEMENT IN DECISION MAKING
"""

from logic.filters import filter_by_interest, filter_by_day
from logic.clash_detector import (
    has_any_clash,
    find_clashes,
    validate_schedule,
    get_time_slots,
    time_to_minutes
)


def select_session_from_parallel(parallel_sessions, user_interest, selected_sessions):
    """
    When multiple sessions run at the same time, select ONE based on deterministic rules
    
    DECISION LOGIC (in order of priority):
    1. If one matches user interest exactly, choose it
    2. If multiple match, choose the first one
    3. If none match, choose the first one
    
    Args:
        parallel_sessions: List of sessions at the same time
        user_interest: 'student' or 'industry'
        selected_sessions: Already selected sessions (to avoid clashes)
    
    Returns:
        Selected session dict
    """
    # Filter out sessions that would clash with already selected ones
    available = [s for s in parallel_sessions if not has_any_clash(selected_sessions, s)]
    
    if not available:
        return None
    
    # Priority 1: Sessions matching user interest
    if user_interest:
        matching = [s for s in available if user_interest in s.get('tags', [])]
        if matching:
            return matching[0]  # Take first match
    
    # Priority 2: Take first available
    return available[0]


def build_schedule(sessions_data, preferences):
    """
    Main schedule building function - PURE LOGIC
    
    Args:
        sessions_data: Dict with 'sessions' key containing all sessions
        preferences: Dict with:
            - interest: 'student' or 'industry'
            - days: number (1 or 2) - optional, default 2
    
    Returns:
        Dict with schedule:
        {
            'day1': [session objects],
            'day2': [session objects],
            'metadata': {
                'total_sessions': int,
                'clashes_resolved': int,
                'validation': {'is_valid': bool, 'errors': []}
            }
        }
    """
    all_sessions = sessions_data.get('sessions', [])
    user_interest = preferences.get('interest', None)
    num_days = preferences.get('days', 2)
    
    # Step 1: Filter sessions based on interest
    filtered_sessions = filter_by_interest(all_sessions, user_interest)
    
    # Step 2: Group sessions by time slots to identify parallel sessions
    time_slots = get_time_slots(filtered_sessions)
    
    # Step 3: Build schedule day by day
    schedule = {}
    clashes_resolved = 0
    
    for day in range(1, num_days + 1):
        day_key = f'day{day}'
        schedule[day_key] = []
        
        # Get sessions for this day
        day_sessions = filter_by_day(filtered_sessions, day)
        
        # Get time slots for this day
        day_slots = {k: v for k, v in time_slots.items() if k.startswith(f'day{day}_')}
        
        # For each time slot, select ONE session
        for slot_key, parallel_sessions in sorted(day_slots.items()):
            selected = select_session_from_parallel(
                parallel_sessions,
                user_interest,
                schedule[day_key]
            )
            
            if selected:
                schedule[day_key].append(selected)
                
                # Track if we had to resolve a clash
                if len(parallel_sessions) > 1:
                    clashes_resolved += 1
    
    # Step 4: Validate the final schedule
    is_valid, errors = validate_schedule(schedule)
    
    # Step 5: Calculate metadata
    total_sessions = sum(len(sessions) for sessions in schedule.values())
    
    metadata = {
        'total_sessions': total_sessions,
        'clashes_resolved': clashes_resolved,
        'user_interest': user_interest,
        'days_planned': num_days,
        'validation': {
            'is_valid': is_valid,
            'errors': errors
        }
    }
    
    schedule['metadata'] = metadata
    
    return schedule


def get_alternative_sessions(sessions_data, selected_session_id, user_interest):
    """
    Find alternative sessions that run at the same time as the selected session
    
    Used when user wants to swap a session
    
    Args:
        sessions_data: Dict with all sessions
        selected_session_id: ID of the session to find alternatives for
        user_interest: User's interest filter
    
    Returns:
        List of alternative sessions at the same time
    """
    all_sessions = sessions_data.get('sessions', [])
    
    # Find the selected session
    selected = next((s for s in all_sessions if s['id'] == selected_session_id), None)
    
    if not selected:
        return []
    
    # Find all sessions on the same day and time
    alternatives = []
    for session in all_sessions:
        if session['id'] == selected_session_id:
            continue
        
        # Same day and time slot
        if (session['day'] == selected['day'] and
            session['start'] == selected['start'] and
            session['end'] == selected['end']):
            alternatives.append(session)
    
    return alternatives


def summarize_schedule(schedule):
    """
    Generate a human-readable summary of the schedule
    
    This is used by the LLM to explain the schedule to the user
    Returns a text summary, NOT the full schedule
    """
    lines = []
    
    metadata = schedule.get('metadata', {})
    
    lines.append(f"📅 Schedule Summary")
    lines.append(f"Total sessions: {metadata.get('total_sessions', 0)}")
    lines.append(f"Interest track: {metadata.get('user_interest', 'general')}")
    
    if metadata.get('clashes_resolved', 0) > 0:
        lines.append(f"Parallel sessions resolved: {metadata['clashes_resolved']}")
    
    lines.append("")
    
    for day_key in ['day1', 'day2']:
        if day_key not in schedule:
            continue
        
        day_num = day_key[-1]
        sessions = schedule[day_key]
        
        lines.append(f"Day {day_num} ({len(sessions)} sessions):")
        for session in sessions:
            lines.append(f"  • {session['start']}-{session['end']}: {session['title']}")
        lines.append("")
    
    return "\n".join(lines)
