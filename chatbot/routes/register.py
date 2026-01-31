"""
Registration Route - API endpoints for registration management
This route handles registration state and submissions
"""

from flask import Blueprint, request, jsonify, session
import json

from logic.registration import (
    start_registration,
    get_current_question,
    process_input,
    get_summary,
    cancel_registration,
    RegistrationState,
    RegistrationSteps
)

register_bp = Blueprint('register', __name__)


# In-memory storage for registration sessions
# In production, use session or database
registration_sessions = {}


def get_session_id():
    """
    Get or create a session ID for the user
    In production, use Flask session or authentication tokens
    """
    if 'session_id' not in session:
        import uuid
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']


@register_bp.route('/api/register/start', methods=['POST'])
def start_registration_session():
    """
    POST /api/register/start
    
    Starts a new registration session
    
    Optional Body:
    {
        "session_id": "optional - provide existing or let server generate"
    }
    
    Returns:
        {
            "message": "...",
            "question": {...},
            "session_id": "...",
            "state": {...}
        }
    """
    try:
        import uuid
        
        # Accept session_id from request body or generate new one
        data = request.get_json() or {}
        session_id = data.get('session_id') or str(uuid.uuid4())
        
        # Initialize registration state
        reg_state = start_registration()
        registration_sessions[session_id] = reg_state
        
        # Get first question
        question = get_current_question(reg_state)
        
        return jsonify({
            "message": "Registration started. Please answer the following questions.",
            "question": question,
            "session_id": session_id,
            "state": reg_state.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": "Failed to start registration",
            "details": str(e)
        }), 500


@register_bp.route('/api/register/answer', methods=['POST'])
def submit_answer():
    """
    POST /api/register/answer
    
    Body:
    {
        "answer": "user's answer",
        "session_id": "optional session id"
    }
    
    Returns:
        {
            "success": bool,
            "message": "...",
            "next_question": {...} or null,
            "completed": bool,
            "summary": "..." (if at confirmation step)
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'answer' not in data:
            return jsonify({"error": "Answer field required"}), 400
        
        # Use session_id from request body if provided, otherwise use Flask session
        session_id = data.get('session_id') or get_session_id()
        user_answer = data['answer']
        
        # Get registration state
        if session_id not in registration_sessions:
            return jsonify({
                "error": "No active registration session. Please start registration first.",
                "action": "start_registration"
            }), 400
        
        reg_state = registration_sessions[session_id]
        
        if not reg_state.is_active:
            return jsonify({
                "error": "Registration session has ended.",
                "action": "start_registration"
            }), 400
        
        # Process the answer
        result = process_input(reg_state, user_answer)
        
        # Update stored state
        registration_sessions[session_id] = reg_state
        
        # If at confirmation step, include summary
        if reg_state.current_step == RegistrationSteps.CONFIRMATION:
            result['summary'] = get_summary(reg_state)
        
        # If completed, clean up session
        if result.get('completed'):
            # In production, save to database here
            completed_data = reg_state.data.copy()
            # For now, just log or store temporarily
            print(f"Registration completed for session {session_id}: {completed_data}")
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            "error": "Failed to process answer",
            "details": str(e)
        }), 500


@register_bp.route('/api/register/cancel', methods=['POST'])
def cancel_registration_session():
    """
    POST /api/register/cancel
    
    Cancels the current registration session
    
    Optional Body:
    {
        "session_id": "optional - provide existing or use Flask session"
    }
    """
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id') or get_session_id()
        
        if session_id in registration_sessions:
            reg_state = registration_sessions[session_id]
            result = cancel_registration(reg_state)
            
            # Clean up
            del registration_sessions[session_id]
            
            return jsonify(result), 200
        else:
            return jsonify({
                "message": "No active registration to cancel."
            }), 200
            
    except Exception as e:
        return jsonify({
            "error": "Failed to cancel registration",
            "details": str(e)
        }), 500


@register_bp.route('/api/register/status', methods=['GET'])
def get_registration_status():
    """
    GET /api/register/status?session_id=xxx
    
    Gets the current registration status
    """
    try:
        # Accept session_id from query parameter or use Flask session
        session_id = request.args.get('session_id') or get_session_id()
        
        if session_id not in registration_sessions:
            return jsonify({
                "active": False,
                "message": "No active registration session."
            }), 200
        
        reg_state = registration_sessions[session_id]
        
        if not reg_state.is_active:
            return jsonify({
                "active": False,
                "message": "Registration session has ended."
            }), 200
        
        question = get_current_question(reg_state)
        summary = None
        
        if reg_state.current_step == RegistrationSteps.CONFIRMATION:
            summary = get_summary(reg_state)
        
        return jsonify({
            "active": True,
            "current_question": question,
            "summary": summary,
            "state": reg_state.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": "Failed to get registration status",
            "details": str(e)
        }), 500
