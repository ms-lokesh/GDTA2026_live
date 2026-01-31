"""
RAG Engine - Retrieval-Augmented Generation for Conference Data

This module provides natural language responses by:
1. Loading conference and session data from JSON files
2. Passing relevant context to LLM
3. Getting natural conversational responses

CRITICAL: Backend logic for registration and planning remains deterministic.
LLM is used ONLY for understanding questions and generating natural responses.
"""

import os
import json
import logging
import re
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


def clean_markdown(text: str) -> str:
    """
    Convert markdown formatting to clean text for professional display
    
    Args:
        text: Text with markdown formatting
        
    Returns:
        Clean text without markdown symbols
    """
    # Remove bold formatting: **text** or __text__
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    
    # Remove italic formatting: *text* or _text_
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    
    # Remove code formatting: `text`
    text = re.sub(r'`(.+?)`', r'\1', text)
    
    # Clean up bullet points
    text = re.sub(r'^\* ', '• ', text, flags=re.MULTILINE)
    text = re.sub(r'^- ', '• ', text, flags=re.MULTILINE)
    
    return text.strip()


class RAGEngine:
    """
    RAG Engine for GDTA 2026 Conference Chatbot
    
    Responsibilities:
    - Load conference data from JSON files
    - Build context for LLM queries
    - Call LLM with grounded prompts
    - Return natural language responses
    
    Does NOT:
    - Make decisions about registration
    - Build schedules (that's planner.py)
    - Modify any data
    """
    
    def __init__(self, conference_data: Dict, sessions_data: Dict):
        """
        Initialize RAG engine with conference data
        
        Args:
            conference_data: Conference info from conference.json
            sessions_data: Sessions from sessions.json
        """
        self.conference_data = conference_data
        self.sessions_data = sessions_data
        self.gemini_key = os.getenv('GOOGLE_API_KEY')
        self.openai_key = os.getenv('OPENAI_API_KEY')
        
    def _build_system_prompt(self) -> str:
        """
        Build grounded system prompt with conference data
        
        This ensures LLM answers ONLY from provided data
        """
        conference_info = json.dumps(self.conference_data, indent=2)
        
        # Get session summary (not full details to save tokens)
        session_count = len(self.sessions_data.get('sessions', []))
        
        return f"""You are the official GDTA 2026 Conference Assistant.

CONFERENCE DATA (YOUR ONLY SOURCE OF TRUTH):
{conference_info}

AVAILABLE SESSIONS: {session_count} sessions across 2 days

CRITICAL RULES:
1. Answer ONLY using the provided conference data
2. If information is not in the data, say "I don't have that information"
3. Never invent dates, times, speakers, or locations
4. Be conversational but factual
5. For session details, you have access to full session data
6. If asked about registration, direct users to say "I want to register"
7. If asked about schedule planning, direct users to say "I need a schedule"

RESPONSE STYLE:
- Friendly and helpful
- Concise but complete
- Use bullet points for lists
- Include specific details (dates, times, locations) when available

Remember: You are providing information only. The backend handles all actions."""

    def _get_relevant_sessions(self, query: str) -> List[Dict]:
        """
        Filter sessions relevant to the query
        
        Simple keyword matching for now. Can be enhanced with embeddings.
        
        Args:
            query: User's question (lowercase)
            
        Returns:
            List of relevant session dictionaries
        """
        query_lower = query.lower()
        sessions = self.sessions_data.get('sessions', [])
        
        # Keywords to search in
        search_fields = ['title', 'description', 'speaker', 'room']
        
        relevant = []
        for session in sessions:
            # Check if any query words appear in session data
            session_text = ' '.join([
                str(session.get(field, '')).lower() 
                for field in search_fields
            ])
            
            # Simple word matching
            query_words = query_lower.split()
            if any(word in session_text for word in query_words if len(word) > 3):
                relevant.append(session)
        
        # If no specific matches, return all sessions (user might want overview)
        if not relevant:
            relevant = sessions
            
        return relevant[:10]  # Limit to 10 most relevant
    
    def _call_gemini(self, user_query: str, context: str, timeout: int = 10) -> Optional[str]:
        """
        Call Google Gemini API for response generation
        
        Args:
            user_query: User's question
            context: Relevant data context
            timeout: Request timeout
            
        Returns:
            Generated response or None on failure
        """
        try:
            from google import genai
            
            client = genai.Client(api_key=self.gemini_key)
            # Use gemini-2.5-flash-lite - better free tier limits
            model_name = 'gemini-2.5-flash-lite'
            
            system_prompt = self._build_system_prompt()
            
            full_prompt = f"""{system_prompt}

RELEVANT SESSION DATA:
{context}

USER QUESTION: {user_query}

ASSISTANT RESPONSE:"""
            
            response = client.models.generate_content(
                model=model_name,
                contents=full_prompt,
                config={
                    'temperature': 0.7,
                    'max_output_tokens': 500,
                }
            )
            
            # Clean markdown formatting for professional display
            return clean_markdown(response.text)
            
        except ImportError:
            logger.warning("Google Generative AI package not installed")
            return None
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return None
    
    def _call_openai(self, user_query: str, context: str, timeout: int = 10) -> Optional[str]:
        """
        Call OpenAI API for response generation (backup)
        
        Args:
            user_query: User's question
            context: Relevant data context
            timeout: Request timeout
            
        Returns:
            Generated response or None on failure
        """
        try:
            import openai
            
            client = openai.OpenAI(api_key=self.openai_key, timeout=timeout)
            
            system_prompt = self._build_system_prompt()
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"RELEVANT SESSION DATA:\n{context}\n\nUSER QUESTION: {user_query}"}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            # Clean markdown formatting for professional display
            return clean_markdown(response.choices[0].message.content)
            
        except ImportError:
            logger.warning("OpenAI package not installed")
            return None
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None
    
    def answer_question(self, user_query: str) -> str:
        """
        Generate natural language answer to user's question
        
        Args:
            user_query: User's question about the conference
            
        Returns:
            Natural language response (grounded in data)
        """
        
        # Get relevant session data
        relevant_sessions = self._get_relevant_sessions(user_query)
        
        # Build context string
        context = json.dumps(relevant_sessions, indent=2)
        
        # Try Gemini first
        response = None
        if self.gemini_key:
            logger.info("Calling Gemini for RAG response")
            response = self._call_gemini(user_query, context)
        
        # Fallback to OpenAI
        if not response and self.openai_key:
            logger.info("Falling back to OpenAI for RAG response")
            response = self._call_openai(user_query, context)
        
        # Ultimate fallback to simple data lookup
        if not response:
            logger.warning("No LLM available, using basic response")
            response = self._fallback_response(user_query)
        
        return response
    
    def _fallback_response(self, user_query: str) -> str:
        """
        Basic fallback response when LLM is unavailable
        
        Args:
            user_query: User's question
            
        Returns:
            Simple structured response
        """
        query_lower = user_query.lower()
        
        # Date questions
        if 'when' in query_lower or 'date' in query_lower:
            return (f"GDTA 2026 takes place from {self.conference_data['dates']['start']} "
                   f"to {self.conference_data['dates']['end']}.")
        
        # Location questions
        elif 'where' in query_lower or 'location' in query_lower or 'venue' in query_lower:
            loc = self.conference_data['location']
            return (f"The conference is at {loc['venue']}, "
                   f"{loc['city']}, {loc['country']}.")
        
        # Session count
        elif 'how many' in query_lower and 'session' in query_lower:
            count = len(self.sessions_data.get('sessions', []))
            return f"There are {count} sessions scheduled across 2 days."
        
        # Default
        else:
            return (f"{self.conference_data['description']} "
                   f"It takes place from {self.conference_data['dates']['start']} "
                   f"to {self.conference_data['dates']['end']} "
                   f"in {self.conference_data['location']['city']}.\n\n"
                   f"How can I help you with the conference?")


def is_rag_available() -> bool:
    """Check if RAG can be used (requires API key)"""
    return bool(os.getenv('GOOGLE_API_KEY') or os.getenv('OPENAI_API_KEY'))
