"""
Conversation Memory Database
Stores conversation context persistently using SQLite
"""
import sqlite3
import json
import os
from datetime import datetime, timedelta
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), 'conversations.db')


class ConversationStore:
    """Persistent storage for conversation contexts"""
    
    def __init__(self):
        self._init_db()
    
    def _init_db(self):
        """Create tables if they don't exist"""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    session_id TEXT PRIMARY KEY,
                    user_type TEXT,
                    last_schedule TEXT,
                    last_action TEXT,
                    history TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
            ''')
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def get_context(self, session_id):
        """Get conversation context for a session"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM conversations WHERE session_id = ?',
                (session_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return {
                    'user_type': row['user_type'],
                    'last_schedule': json.loads(row['last_schedule']) if row['last_schedule'] else None,
                    'last_action': row['last_action'],
                    'history': json.loads(row['history']) if row['history'] else []
                }
            return None
    
    def save_context(self, session_id, user_type=None, last_schedule=None, 
                     last_action=None, history=None):
        """Save or update conversation context"""
        now = datetime.now().isoformat()
        
        with self._get_connection() as conn:
            # Check if exists
            cursor = conn.execute(
                'SELECT session_id FROM conversations WHERE session_id = ?',
                (session_id,)
            )
            exists = cursor.fetchone()
            
            if exists:
                # Update existing
                conn.execute('''
                    UPDATE conversations 
                    SET user_type = COALESCE(?, user_type),
                        last_schedule = COALESCE(?, last_schedule),
                        last_action = COALESCE(?, last_action),
                        history = COALESCE(?, history),
                        updated_at = ?
                    WHERE session_id = ?
                ''', (
                    user_type,
                    json.dumps(last_schedule) if last_schedule is not None else None,
                    last_action,
                    json.dumps(history) if history is not None else None,
                    now,
                    session_id
                ))
            else:
                # Insert new
                conn.execute('''
                    INSERT INTO conversations 
                    (session_id, user_type, last_schedule, last_action, history, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session_id,
                    user_type,
                    json.dumps(last_schedule) if last_schedule else None,
                    last_action,
                    json.dumps(history) if history else '[]',
                    now,
                    now
                ))
            conn.commit()
    
    def add_message(self, session_id, role, content):
        """Add a message to conversation history"""
        context = self.get_context(session_id)
        
        if context is None:
            history = []
        else:
            history = context['history']
        
        history.append({'role': role, 'content': content})
        
        # Keep only last 10 messages
        if len(history) > 10:
            history = history[-10:]
        
        self.save_context(session_id, history=history)
    
    def delete_context(self, session_id):
        """Delete conversation context (user ends conversation)"""
        with self._get_connection() as conn:
            conn.execute('DELETE FROM conversations WHERE session_id = ?', (session_id,))
            conn.commit()
    
    def cleanup_old_sessions(self, hours=12):
        """Delete sessions older than specified hours"""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                'DELETE FROM conversations WHERE updated_at < ?',
                (cutoff,)
            )
            conn.commit()


# Global instance
_store = None

def get_conversation_store():
    """Get or create conversation store instance"""
    global _store
    if _store is None:
        _store = ConversationStore()
    return _store
