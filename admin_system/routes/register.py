"""
Registration Route - API endpoints for registration management
This route handles registration state and submissions
"""

from flask import Blueprint, request, jsonify, session as flask_session
import json
import pickle
import base64

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
# In production, use database
registration_sessions = {}


def serialize_state(state):
    """Serialize state object to store in session"""
    return base64.b64encode(pickle.dumps(state)).decode('utf-8')


def deserialize_state(state_str):
    """Deserialize state object from session"""
    return pickle.loads(base64.b64decode(state_str.encode('utf-8')))


def get_or_create_session_id():
    """
    Get or create a session ID for the user
    """
    if 'reg_session_id' not in flask_session:
        import uuid
        flask_session['reg_session_id'] = str(uuid.uuid4())
        flask_session.modified = True
    return flask_session['reg_session_id']


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
        
        print(f"[DEBUG] Starting registration with session_id: {session_id}")
        
        # Initialize registration state
        reg_state = start_registration()
        
        # Store in both memory and Flask session for redundancy
        registration_sessions[session_id] = reg_state
        flask_session['reg_state'] = serialize_state(reg_state)
        flask_session['reg_session_id'] = session_id
        flask_session.modified = True
        
        print(f"[DEBUG] Registration session created. Active sessions: {list(registration_sessions.keys())}")
        print(f"[DEBUG] Flask session ID: {flask_session.get('reg_session_id')}")
        print(f"[DEBUG] Registration sessions dict id: {id(registration_sessions)}")
        
        # Get first question
        question = get_current_question(reg_state)
        
        return jsonify({
            "message": "Registration started. Please answer the following questions.",
            "question": question,
            "session_id": session_id,
            "state": reg_state.to_dict()
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Failed to start registration: {e}")
        import traceback
        traceback.print_exc()
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
        
        print(f"[DEBUG] Received data: {data}")
        print(f"[DEBUG] Request headers: {dict(request.headers)}")
        
        if not data or 'answer' not in data:
            print(f"[ERROR] Missing answer field. Data received: {data}")
            return jsonify({"error": "Answer field required", "received": data}), 400
        
        # Use session_id from request body if provided, otherwise use Flask session
        session_id = data.get('session_id') or flask_session.get('reg_session_id')
        user_answer = data['answer']
        
        print(f"[DEBUG] Session ID from request: {data.get('session_id')}")
        print(f"[DEBUG] Session ID from Flask session: {flask_session.get('reg_session_id')}")
        print(f"[DEBUG] Using session ID: {session_id}")
        print(f"[DEBUG] Active sessions in memory: {list(registration_sessions.keys())}")
        print(f"[DEBUG] Registration sessions dict id: {id(registration_sessions)}")
        print(f"[DEBUG] Flask session has reg_state: {'reg_state' in flask_session}")
        
        # Try to get registration state from memory first, then Flask session
        reg_state = None
        
        if session_id and session_id in registration_sessions:
            print(f"[DEBUG] Found session in memory")
            reg_state = registration_sessions[session_id]
        elif 'reg_state' in flask_session:
            print(f"[DEBUG] Found session in Flask session, deserializing...")
            try:
                reg_state = deserialize_state(flask_session['reg_state'])
                # Restore to memory
                if session_id:
                    registration_sessions[session_id] = reg_state
                print(f"[DEBUG] Successfully restored from Flask session")
            except Exception as e:
                print(f"[ERROR] Failed to deserialize state: {e}")
        
        if not reg_state:
            print(f"[ERROR] Session {session_id} not found in memory or Flask session")
            return jsonify({
                "error": "No active registration session. Please start registration first.",
                "action": "start_registration"
            }), 400
        
        if not reg_state.is_active:
            return jsonify({
                "error": "Registration session has ended.",
                "action": "start_registration"
            }), 400
        
        # Process the answer
        result = process_input(reg_state, user_answer)
        
        # Update stored state in both places
        if session_id:
            registration_sessions[session_id] = reg_state
        flask_session['reg_state'] = serialize_state(reg_state)
        flask_session.modified = True
        
        # If at confirmation step, include summary
        if reg_state.current_step == RegistrationSteps.CONFIRMATION:
            result['summary'] = get_summary(reg_state)
        
        # If completed, clean up session
        if result.get('completed'):
            # Save to database
            completed_data = reg_state.data.copy()
            completed_data['session_id'] = session_id  # Add session_id for tracking
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


@register_bp.route('/api/register/submit-form', methods=['POST'])
def submit_form_registration():
    """
    POST /api/register/submit-form
    
    Direct form-based registration submission
    Accepts all registration data at once and submits to the same backend as chatbot
    
    Body:
    {
        "name": "...",
        "email": "...",
        "institution": "...",
        "role": "...",
        "gdta_member": "Yes/No",
        "gdta_affiliation": "...",
        "country": "...",
        "state": "...",
        "consent": "Yes"
    }
    
    Returns:
        {
            "success": true/false,
            "message": "...",
            "registration_id": "..." (if successful)
        }
    """
    try:
        from logic.registration import submit_registration
        
        # Get form data from request
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "message": "No data provided"
            }), 400
        
        # Prepare registration data with form source
        registration_data = {
            "name": data.get("name", "").strip(),
            "email": data.get("email", "").strip(),
            "institution": data.get("institution", "").strip(),
            "role": data.get("role", "").strip(),
            "gdta_member": data.get("gdta_member", "").strip(),
            "gdta_affiliation": data.get("gdta_affiliation", "").strip(),
            "country": data.get("country", "").strip(),
            "state": data.get("state", "").strip(),
            "consent": data.get("consent", "").strip(),
            "registration_category": data.get("registration_category", "").strip(),
            "addon_food_accommodation": data.get("addon_food_accommodation", "No"),
            "addon_safari": data.get("addon_safari", "No"),
            "safari_route": data.get("safari_route", "").strip(),
            "fee_currency": data.get("fee_currency"),
            "base_fee": data.get("base_fee"),
            "addon_food_accommodation_fee": data.get("addon_food_accommodation_fee"),
            "addon_safari_fee": data.get("addon_safari_fee"),
            "total_fee": data.get("total_fee"),
            "registration_source": "form"  # Mark as form registration
        }
        
        # Submit registration using the same backend logic
        result = submit_registration(registration_data)
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"Form registration error: {e}")
        return jsonify({
            "success": False,
            "message": "An error occurred during registration. Please try again.",
            "error": str(e)
        }), 500
