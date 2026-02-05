"""
Cleanup endpoint for ending conversations
"""
from flask import Blueprint, request, jsonify, session
from db.conversation_store import get_conversation_store
import logging

cleanup_bp = Blueprint('cleanup', __name__)
logger = logging.getLogger(__name__)


@cleanup_bp.route('/api/conversation/end', methods=['POST'])
def end_conversation():
    """
    End conversation and delete user data
    
    POST /api/conversation/end
    
    Body (optional):
    {
        "session_id": "uuid"  // If not provided, uses current session
    }
    """
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id') or session.get('session_id')
        
        if not session_id:
            return jsonify({'error': 'No active session'}), 400
        
        store = get_conversation_store()
        store.delete_context(session_id)
        
        return jsonify({
            'message': 'Conversation ended and data deleted',
            'session_id': session_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error ending conversation: {e}")
        return jsonify({'error': str(e)}), 500


@cleanup_bp.route('/api/conversation/cleanup', methods=['POST'])
def cleanup_old_conversations():
    """
    Admin endpoint to cleanup old conversations
    
    POST /api/conversation/cleanup
    
    Body (optional):
    {
        "hours": 12  // Delete sessions older than this many hours (default: 12)
    }
    """
    try:
        data = request.get_json() or {}
        hours = data.get('hours', 12)
        
        store = get_conversation_store()
        store.cleanup_old_sessions(hours=hours)
        
        return jsonify({
            'message': f'Cleaned up conversations older than {hours} hours'
        }), 200
        
    except Exception as e:
        logger.error(f"Error cleaning up conversations: {e}")
        return jsonify({'error': str(e)}), 500
