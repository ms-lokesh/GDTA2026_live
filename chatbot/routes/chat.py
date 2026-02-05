"""
Chat Route - API endpoint for conversational interface
This route handles chat messages and manages conversation state

NOW ENHANCED WITH: LLM-based semantic intent resolution
"""

from flask import Blueprint, request, jsonify, session
import json
import os
import uuid
import logging

# Import our logic modules
from logic.planner import build_schedule, summarize_schedule
from logic.registration import (
    start_registration,
    get_current_question,
    process_input,
    get_summary,
    cancel_registration,
    RegistrationSteps
)

# Import LLM intent resolver and RAG engine
try:
    from llm.intent_resolver import resolve_intent, IntentType, is_llm_available
    from llm.rag_engine import RAGEngine, is_rag_available
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    logging.warning("LLM module not available, using keyword fallback only")

# Import conversation store
from db.conversation_store import get_conversation_store

chat_bp = Blueprint('chat', __name__)
logger = logging.getLogger(__name__)

# In-memory storage for registration sessions
registration_sessions = {}
conversation_contexts = {}


class ConversationContext:
    """Track conversation state and history"""
    def __init__(self):
        self.user_type = None  # 'student' or 'industry'
        self.last_schedule = None  # Last generated schedule
        self.last_action = None  # Last action performed
        self.history = []  # Conversation history
    
    def add_message(self, role: str, content: str):
        """Add message to history"""
        self.history.append({'role': role, 'content': content})
        # Keep only last 10 messages
        if len(self.history) > 10:
            self.history = self.history[-10:]


def get_session_id():
    """Get or create a session ID for the user"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']


def load_conference_data():
    """Load conference info from JSON file"""
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'conference.json')
    with open(data_path, 'r') as f:
        return json.load(f)


def load_sessions_data():
    """Load sessions from JSON file"""
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'sessions.json')
    with open(data_path, 'r') as f:
        return json.load(f)


def extract_parameters(user_message: str, context: dict) -> dict:
    """
    Extract parameters from user message
    
    Args:
        user_message: User's input
        context: Current conversation context dict
        
    Returns:
        Dict with extracted parameters
    """
    import re
    
    params = {}
    msg_lower = user_message.lower()
    
    # Extract user type
    if 'student' in msg_lower:
        params['user_type'] = 'student'
    elif 'industry' in msg_lower or 'professional' in msg_lower:
        params['user_type'] = 'industry'
    elif context and context.get('user_type'):
        # Use previously identified user type
        params['user_type'] = context['user_type']
    
    # Extract number of sessions/days
    # Match patterns like "3 sessions", "3 session", "5 per day"
    session_match = re.search(r'(\d+)\s*(session|per\s*day)', msg_lower)
    if session_match:
        params['sessions_per_day'] = int(session_match.group(1))
    
    day_match = re.search(r'(\d+)\s*day', msg_lower)
    if day_match:
        params['num_days'] = int(day_match.group(1))
    
    # Detect modification intent
    modification_keywords = ['change', 'modify', 'update', 'different', 'instead', 'rather']
    if any(keyword in msg_lower for keyword in modification_keywords):
        params['is_modification'] = True
    
    return params


def call_llm_for_response(user_message, context, state):
    """
    Placeholder function for LLM integration
    
    In production, this would call OpenAI, Claude, or another LLM
    The LLM is used ONLY for:
    - Understanding natural language
    - Generating human-friendly responses
    - Asking clarifying questions
    
    The LLM does NOT:
    - Make scheduling decisions
    - Calculate anything
    - Decide which sessions to include
    
    Args:
        user_message: The user's input text
        context: Relevant data (conference info, sessions, etc.)
        state: Current conversation state
    
    Returns:
        Response text from LLM
    """
    # MOCK IMPLEMENTATION - Replace with real LLM call
    # This is where you'd integrate OpenAI API, Claude API, etc.
    
    if state == 'info_mode':
        return f"I'm here to help you with information about GDTA 2026. You asked: '{user_message}'. For conference details, check the conference data. Would you like me to help you build a personalized schedule?"
    
    elif state == 'planning_mode':
        return f"I'm in planning mode. You said: '{user_message}'. Are you a student or industry professional? This helps me recommend the right sessions for you."
    
    else:
        return "How can I help you today?"


@chat_bp.route('/api/chat', methods=['POST'])
def chat():
    """
    POST /api/chat
    
    Body:
    {
        "message": "user text",
        "state": "info_mode" | "planning_mode" | null
    }
    
    The backend controls the flow:
    1. Receives user message
    2. Determines what action to take
    3. Calls appropriate logic functions
    4. Uses LLM only for language understanding/generation
    5. Returns structured response
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({'error': 'message field required'}), 400
        
        user_message = data['message'].lower()
        current_state = data.get('state', 'info_mode')
        
        # Load data
        conference_data = load_conference_data()
        sessions_data = load_sessions_data()
        
        # BACKEND DECISION LOGIC - determine what to do
        response = {
            'message': '',
            'state': current_state,
            'action': None,
            'data': None,
            'session_id': None
        }
        
        # Get or create conversation context from database
        session_id = get_session_id()
        response['session_id'] = session_id
        
        store = get_conversation_store()
        context = store.get_context(session_id) or {}
        
        # Add user message to history
        store.add_message(session_id, 'user', data['message'])
        
        # Extract parameters from message
        extracted_params = extract_parameters(data['message'], context)
        print(f"[DEBUG] Extracted params: {extracted_params}")
        print(f"[DEBUG] Context user_type: {context.get('user_type')}, last_schedule: {context.get('last_schedule') is not None}")
        logger.info(f"Extracted params: {extracted_params}")
        logger.info(f"Context user_type: {context.get('user_type')}, last_schedule: {context.get('last_schedule') is not None}")
        
        # Check if user is in active registration mode
        if session_id in registration_sessions and registration_sessions[session_id].is_active:
            # Handle registration flow
            reg_state = registration_sessions[session_id]
            
            # Check for cancel command
            if user_message in ['cancel', 'exit', 'quit', 'stop']:
                result = cancel_registration(reg_state)
                del registration_sessions[session_id]
                response['state'] = 'info_mode'
                response['message'] = result['message']
                return jsonify(response), 200
            
            # Process registration input
            result = process_input(reg_state, data['message'])  # Use original message, not lowercased
            
            if result['success']:
                if result['completed']:
                    response['state'] = 'info_mode'
                    response['action'] = 'registration_completed'
                    response['message'] = result['message']
                    response['data'] = reg_state.data
                    # Clean up session
                    del registration_sessions[session_id]
                else:
                    response['state'] = 'registration_mode'
                    response['message'] = result['message']
                    
                    # Add next question if available
                    if result.get('next_question'):
                        response['message'] += "\n\n" + result['next_question']['question']
                        if result['next_question'].get('options'):
                            response['message'] += "\nOptions: " + ", ".join(result['next_question']['options'])
                    
                    # Add summary if at confirmation step
                    if result.get('summary'):
                        response['message'] = result['summary']
            else:
                response['state'] = 'registration_mode'
                response['message'] = result['message']
            
            return jsonify(response), 200
        
        # ================================================================
        # INTENT RESOLUTION LAYER
        # Uses LLM for semantic understanding, falls back to keywords
        # Backend routing logic remains unchanged
        # ================================================================
        
        # Resolve intent using LLM or keyword fallback
        use_llm = os.getenv('LLM_ENABLED', 'False').lower() == 'true'
        confidence_threshold = float(os.getenv('LLM_CONFIDENCE_THRESHOLD', '0.6'))
        timeout = int(os.getenv('LLM_TIMEOUT', '5'))
        
        intent_result = None
        if LLM_AVAILABLE:
            try:
                intent_result = resolve_intent(
                    user_message,
                    confidence_threshold=confidence_threshold,
                    use_llm=use_llm,
                    timeout=timeout
                )
                logger.info(f"Intent resolved: {intent_result.intent.value} "
                           f"(confidence: {intent_result.confidence:.2f}, "
                           f"fallback: {intent_result.fallback_used})")
            except Exception as e:
                logger.error(f"Intent resolution failed: {e}")
                intent_result = None
        
        # If intent resolution failed completely, use legacy keyword matching
        if intent_result is None:
            logger.debug("Using legacy keyword routing")
            # Fall through to original keyword matching below
            intent = None
        else:
            intent = intent_result.intent
        
        # ================================================================
        # BACKEND ROUTING - Based on resolved intent
        # All decision logic remains in backend control
        # ================================================================
        
        # Check if it's a modification request (BEFORE route matching)
        is_modification_intent = (
            extracted_params.get('is_modification') or 
            any(word in user_message for word in ['make it', 'change to', 'modify to']) or
            (extracted_params.get('sessions_per_day') or extracted_params.get('num_days'))
        )
        print(f"[DEBUG] Intent: {intent}, is_modification: {is_modification_intent}")
        logger.info(f"Intent: {intent}, is_modification: {is_modification_intent}")
        
        # Route 1: Start Registration
        if intent == IntentType.START_REGISTRATION or (
            intent is None and any(word in user_message for word in ['register', 'registration', 'sign up', 'signup'])
        ):
            response['state'] = 'registration_mode'
            
            # Start registration
            reg_state = start_registration()
            registration_sessions[session_id] = reg_state
            
            question = get_current_question(reg_state)
            response['action'] = 'registration_started'
            response['message'] = "I'll help you with registration. Please answer the following questions.\n\n"
            response['message'] += question['question']
            if question.get('options'):
                response['message'] += "\nOptions: " + ", ".join(question['options'])
            response['message'] += "\n\n(Type 'cancel' at any time to exit registration)"
            
            return jsonify(response), 200
        
        # Route 2: Schedule Request (including modifications)
        elif intent == IntentType.SCHEDULE_REQUEST or is_modification_intent or (
            intent is None and any(word in user_message for word in ['schedule', 'plan', 'recommend', 'sessions'])
        ):
            response['state'] = 'planning_mode'
            
            # Check if this is a modification of existing schedule
            if extracted_params.get('is_modification') and context.get('last_schedule'):
                # Modifying existing schedule
                user_type = context['user_type']  # Use stored user type
                preferences = {'interest': user_type, 'days': 2}
                
                # Apply modifications
                if extracted_params.get('sessions_per_day'):
                    preferences['sessions_per_day'] = extracted_params['sessions_per_day']
                if extracted_params.get('num_days'):
                    preferences['days'] = extracted_params['num_days']
                
                # Build modified schedule
                schedule = build_schedule(sessions_data, preferences)
                
                # Save to database
                store.save_context(session_id, last_schedule=schedule, last_action='schedule_modified')
                
                response['action'] = 'schedule_created'
                response['data'] = schedule
                response['message'] = f"I've updated your schedule for {user_type}s"
                if extracted_params.get('sessions_per_day'):
                    response['message'] += f" with {extracted_params['sessions_per_day']} sessions per day"
                response['message'] += ". Here's your modified schedule:\n\n"
                response['message'] += summarize_schedule(schedule)
                response['message'] += "\n\nAll sessions were selected to avoid time conflicts."
                
            # Check if user type is in message or stored in context
            elif extracted_params.get('user_type'):
                user_type = extracted_params['user_type']
                
                # BUILD SCHEDULE using our logic
                preferences = {'interest': user_type, 'days': 2}
                
                # Apply any specified preferences
                if extracted_params.get('sessions_per_day'):
                    preferences['sessions_per_day'] = extracted_params['sessions_per_day']
                if extracted_params.get('num_days'):
                    preferences['days'] = extracted_params['num_days']
                
                schedule = build_schedule(sessions_data, preferences)
                
                # Save to database
                store.save_context(session_id, user_type=user_type, last_schedule=schedule, last_action='schedule_created')
                
                response['action'] = 'schedule_created'
                response['data'] = schedule
                user_type_display = "students" if user_type == 'student' else "industry professionals"
                response['message'] = f"I've created a personalized {preferences['days']}-day schedule for {user_type_display}"
                if extracted_params.get('sessions_per_day'):
                    response['message'] += f" with {extracted_params['sessions_per_day']} sessions per day"
                response['message'] += ". Here's what I selected:\n\n"
                response['message'] += summarize_schedule(schedule)
                response['message'] += "\n\nAll sessions were selected to avoid time conflicts. Would you like to modify it?"
                
            else:
                # Need clarification - but check if we already know user type
                if context.get('user_type'):
                    # We know the user type, just build the schedule
                    user_type = context['user_type']
                    preferences = {'interest': user_type, 'days': 2}
                    
                    if extracted_params.get('sessions_per_day'):
                        preferences['sessions_per_day'] = extracted_params['sessions_per_day']
                    if extracted_params.get('num_days'):
                        preferences['days'] = extracted_params['num_days']
                    
                    schedule = build_schedule(sessions_data, preferences)
                    
                    # Save to database
                    store.save_context(session_id, last_schedule=schedule, last_action='schedule_created')
                    
                    response['action'] = 'schedule_created'
                    response['data'] = schedule
                    user_type_display = "students" if user_type == 'student' else "industry professionals"
                    response['message'] = f"I've created a personalized {preferences['days']}-day schedule for {user_type_display}"
                    if extracted_params.get('sessions_per_day'):
                        response['message'] += f" with {extracted_params['sessions_per_day']} sessions per day"
                    response['message'] += ". Here's what I selected:\n\n"
                    response['message'] += summarize_schedule(schedule)
                    response['message'] += "\n\nAll sessions were selected to avoid time conflicts. Would you like to modify it?"
                else:
                    # Ask for user type
                    response['message'] = "I'd be happy to create a schedule for you! Are you a student or an industry professional? This helps me recommend the most relevant sessions."
        
        # Route 3: Conference Information
        elif intent == IntentType.CONFERENCE_INFO or (
            intent is None and any(word in user_message for word in ['when', 'where', 'location', 'date', 'what is'])
        ):
            response['state'] = 'info_mode'
            
            # Use RAG engine for natural language responses
            if LLM_AVAILABLE and is_rag_available():
                try:
                    rag_engine = RAGEngine(conference_data, sessions_data)
                    response['message'] = rag_engine.answer_question(data['message'])
                except Exception as e:
                    logger.error(f"RAG engine error: {e}")
                    # Fallback to basic response
                    if 'when' in user_message or 'date' in user_message:
                        response['message'] = f"GDTA 2026 takes place on {conference_data['dates']['start']} to {conference_data['dates']['end']}."
                    elif 'where' in user_message or 'location' in user_message:
                        response['message'] = f"The conference is at {conference_data['location']['venue']}, {conference_data['location']['city']}, {conference_data['location']['country']}."
                    else:
                        response['message'] = f"{conference_data['description']} It takes place {conference_data['dates']['start']} to {conference_data['dates']['end']} in {conference_data['location']['city']}."
            else:
                # Fallback when no LLM available
                if 'when' in user_message or 'date' in user_message:
                    response['message'] = f"GDTA 2026 takes place on {conference_data['dates']['start']} to {conference_data['dates']['end']}."
                elif 'where' in user_message or 'location' in user_message:
                    response['message'] = f"The conference is at {conference_data['location']['venue']}, {conference_data['location']['city']}, {conference_data['location']['country']}."
                else:
                    response['message'] = f"{conference_data['description']} It takes place {conference_data['dates']['start']} to {conference_data['dates']['end']} in {conference_data['location']['city']}."
        
        # Route 4: Greeting
        elif intent == IntentType.GREETING or (
            intent is None and any(word in user_message for word in ['hello', 'hi', 'hey'])
        ):
            response['message'] = "Hello! I'm the GDTA 2026 assistant. I can help you with:\n• Conference information\n• Building a personalized schedule\n• Finding sessions that match your interests\n• Registration for the conference\n\nHow can I help you today?"
        
        # Route 5: Help
        elif intent == IntentType.HELP:
            response['message'] = "I'm here to assist you with GDTA 2026! I can help you with:\n\n• Conference details (dates, location, venue)\n• Registration for the event\n• Building a personalized schedule\n• Finding sessions that match your interests\n• Answering questions about the conference\n\nWhat would you like to know?"
        
        # Route 6: Unknown or Unsupported - Use RAG for any other questions
        else:
            if LLM_AVAILABLE and is_rag_available():
                try:
                    rag_engine = RAGEngine(conference_data, sessions_data)
                    response['message'] = rag_engine.answer_question(data['message'])
                except Exception as e:
                    logger.error(f"RAG engine error: {e}")
                    response['message'] = "I can help you with conference information, registration, and schedule planning. What would you like to know?"
            else:
                response['message'] = "I can help you with conference information, registration, and schedule planning. What would you like to know?"
        
        # Add assistant response to conversation history
        store.add_message(session_id, 'assistant', response['message'])
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to process message',
            'details': str(e)
        }), 500


@chat_bp.route('/api/state', methods=['POST'])
def update_state():
    """
    POST /api/state
    
    Body:
    {
        "state": "info_mode" | "planning_mode"
    }
    
    Allows frontend to explicitly update conversation state
    """
    try:
        data = request.get_json()
        new_state = data.get('state')
        
        if new_state not in ['info_mode', 'planning_mode', 'registration_mode']:
            return jsonify({'error': 'Invalid state'}), 400
        
        # In a real app, store this in session or database
        return jsonify({
            'state': new_state,
            'message': f'State updated to {new_state}'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
