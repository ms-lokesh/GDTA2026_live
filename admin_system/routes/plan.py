"""
Plan Route - API endpoint for schedule building
This route exposes the planning logic as an API
"""

from flask import Blueprint, request, jsonify
import json
import os

# Import our deterministic logic
from logic.planner import build_schedule, get_alternative_sessions

plan_bp = Blueprint('plan', __name__)


def load_sessions_data():
    """Load sessions from JSON file"""
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'sessions.json')
    with open(data_path, 'r') as f:
        return json.load(f)


@plan_bp.route('/api/sessions', methods=['GET'])
def get_all_sessions():
    """
    GET /api/sessions
    
    Returns all sessions from the JSON file
    No filtering, no AI - just raw data
    """
    try:
        sessions_data = load_sessions_data()
        return jsonify(sessions_data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@plan_bp.route('/api/plan', methods=['POST'])
def create_plan():
    """
    POST /api/plan
    
    Body:
    {
        "interest": "student" | "industry",
        "days": 1 | 2  (optional, default 2)
    }
    
    Returns:
    {
        "day1": [sessions],
        "day2": [sessions],
        "metadata": {...}
    }
    
    IMPORTANT: All decisions are made by logic/planner.py
    NO AI involvement in schedule building
    """
    try:
        # Parse request
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        interest = data.get('interest')
        days = data.get('days', 2)
        
        # Validate interest
        if interest not in ['student', 'industry', None]:
            return jsonify({
                'error': 'interest must be "student" or "industry"'
            }), 400
        
        # Validate days
        if days not in [1, 2]:
            return jsonify({
                'error': 'days must be 1 or 2'
            }), 400
        
        # Load session data
        sessions_data = load_sessions_data()
        
        # Build schedule using DETERMINISTIC LOGIC
        preferences = {
            'interest': interest,
            'days': days
        }
        
        schedule = build_schedule(sessions_data, preferences)
        
        # Return the schedule
        return jsonify(schedule), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to build schedule',
            'details': str(e)
        }), 500


@plan_bp.route('/api/alternatives/<session_id>', methods=['GET'])
def get_alternatives(session_id):
    """
    GET /api/alternatives/<session_id>
    
    Query params:
        ?interest=student|industry
    
    Returns alternative sessions at the same time slot
    Used when user wants to swap sessions
    """
    try:
        interest = request.args.get('interest')
        sessions_data = load_sessions_data()
        
        alternatives = get_alternative_sessions(sessions_data, session_id, interest)
        
        return jsonify({
            'session_id': session_id,
            'alternatives': alternatives
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@plan_bp.route('/api/validate', methods=['POST'])
def validate_custom_schedule():
    """
    POST /api/validate
    
    Body:
    {
        "day1": [session_ids],
        "day2": [session_ids]
    }
    
    Validates a custom schedule for clashes
    Returns validation result
    """
    try:
        from logic.clash_detector import validate_schedule
        
        data = request.get_json()
        sessions_data = load_sessions_data()
        all_sessions = {s['id']: s for s in sessions_data['sessions']}
        
        # Convert IDs to full session objects
        schedule = {}
        for day_key, session_ids in data.items():
            schedule[day_key] = [all_sessions[sid] for sid in session_ids if sid in all_sessions]
        
        is_valid, errors = validate_schedule(schedule)
        
        return jsonify({
            'valid': is_valid,
            'errors': errors
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
