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
        self.gemini_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
        self.grok_key = os.getenv('GROK_API_KEY')
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
- For pricing questions, always include category-wise fee details and mention GST note when available

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
            import google.generativeai as genai
            
            genai.configure(api_key=self.gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            system_prompt = self._build_system_prompt()
            
            full_prompt = f"""{system_prompt}

RELEVANT SESSION DATA:
{context}

USER QUESTION: {user_query}

ASSISTANT RESPONSE:"""
            
            response = model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=500
                )
            )
            
            # Clean markdown formatting for professional display
            return clean_markdown(response.text)
            
        except ImportError:
            logger.warning("Google Generative AI package not installed")
            return None
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return None
    
    def _call_grok(self, user_query: str, context: str, timeout: int = 10) -> Optional[str]:
        """
        Call Grok API for response generation
        
        Args:
            user_query: User's question
            context: Relevant data context
            timeout: Request timeout
            
        Returns:
            Generated response or None on failure
        """
        try:
            import openai
            
            # Grok uses OpenAI-compatible API
            client = openai.OpenAI(
                api_key=self.grok_key,
                base_url="https://api.x.ai/v1",
                timeout=timeout
            )
            
            system_prompt = self._build_system_prompt()
            
            response = client.chat.completions.create(
                model="grok-beta",
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
            logger.warning("OpenAI package not installed (required for Grok)")
            return None
        except Exception as e:
            logger.error(f"Grok API error: {e}")
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
        context_payload = {
            "conference": self.conference_data,
            "relevant_sessions": relevant_sessions
        }
        context = json.dumps(context_payload, indent=2)
        
        # Try Gemini first
        response = None
        if self.gemini_key:
            logger.info("Calling Gemini for RAG response")
            response = self._call_gemini(user_query, context)
        
        # Try Grok next
        if not response and self.grok_key:
            logger.info("Trying Grok for RAG response")
            response = self._call_grok(user_query, context)
        
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
        contact = self.conference_data.get('contact', {})
        travel = self.conference_data.get('travel_and_stay', {})
        hackathon = self.conference_data.get('hackathon', {})

        asks_date = any(word in query_lower for word in ['when', 'date'])
        asks_location = any(word in query_lower for word in ['where', 'location', 'venue'])
        
        # Explicit unknown-fact probes
        if any(word in query_lower for word in ['chief guest', 'prize money', 'exact prize', 'cash prize']):
            return "I don't have that information in the current GDTA 2026 conference data."

        # Combined date + location questions
        if asks_date and asks_location:
            loc = self.conference_data['location']
            return (
                f"GDTA 2026 takes place from {self.conference_data['dates']['start']} to {self.conference_data['dates']['end']}, "
                f"at {loc['venue']}, {loc['city']}, {loc['country']}."
            )

        # Date questions
        if asks_date:
            return (f"GDTA 2026 takes place from {self.conference_data['dates']['start']} "
                   f"to {self.conference_data['dates']['end']}.")

        # Travel / stay questions (check before generic location)
        elif any(word in query_lower for word in ['travel', 'stay', 'hotel', 'airport', 'train', 'road', 'reach']):
            travel_info = travel.get('travel', {})
            return (
                "Travel & Stay info for GDTA 2026:\n"
                f"• By Air: {travel_info.get('air', 'Details not available')}\n"
                f"• By Train: {travel_info.get('train', 'Details not available')}\n"
                f"• By Road: {travel_info.get('road', 'Details not available')}\n"
                "• Recommended hotels are listed by area: near airport, near SNS, and city center on the Travel & Stay page."
            )
        
        # Location questions
        elif asks_location:
            loc = self.conference_data['location']
            return (f"The conference is at {loc['venue']}, "
                   f"{loc['city']}, {loc['country']}.")

        # Contact questions
        elif any(word in query_lower for word in ['contact', 'email', 'phone', 'reach', 'support']):
            email = contact.get('email', 'Not available')
            phone = contact.get('phone', 'Not available')
            address = contact.get('address', self.conference_data.get('location', {}).get('display', 'Not available'))
            return (
                "Here are the GDTA 2026 contact details:\n"
                f"• Email: {email}\n"
                f"• Phone: {phone}\n"
                f"• Address: {address}"
            )

        # Pricing / fee questions
        elif any(word in query_lower for word in ['fee', 'fees', 'price', 'pricing', 'cost', 'charges']):
            pricing = self.conference_data.get('pricing', {})
            if pricing:
                return (
                    "Here are the GDTA 2026 registration fees:\n"
                    "• Students: Base Rs.500; Food & Accommodation add-on Rs.1000; Safari add-on Rs.1500\n"
                    "• Academicians: Base Rs.2000; Food & Accommodation add-on Rs.2500; Safari add-on Rs.3000\n"
                    "• Industry People: Rs.7500 (all-inclusive)\n"
                    "• Foreign Delegates: $100 (all-inclusive)\n"
                    "Note: GST will be added at the final payment stage."
                )
            return "I don't have pricing details at the moment. Please contact the organizers for the latest fee structure."

        # Safari route questions
        elif 'safari' in query_lower and any(word in query_lower for word in ['route', 'routes', 'which', 'options']):
            routes = self.conference_data.get('safari_routes', [])
            if routes:
                return "Available safari routes:\n" + "\n".join([f"• {r}" for r in routes])
            return "Safari route details are not available right now."

        # Hackathon questions
        elif any(word in query_lower for word in ['hackathon', 'challenge']):
            hack_tracks = hackathon.get('tracks', [])
            timeline = hackathon.get('timeline', {})
            tracks_text = "\n".join([f"• {t}" for t in hack_tracks]) if hack_tracks else "• Track details coming soon"
            return (
                "GDTA Challenge 2026 (Hackathon) details:\n"
                f"• Focus: {hackathon.get('summary', 'AI innovation for real-world impact')}\n"
                f"• Registration Opens: {timeline.get('registration_opens', 'N/A')}\n"
                f"• Kickoff: {timeline.get('kickoff', 'N/A')}\n"
                f"• Submission Deadline: {timeline.get('submission_deadline', 'N/A')}\n"
                "• Tracks:\n"
                f"{tracks_text}"
            )

        # Conference tracks questions
        elif any(word in query_lower for word in ['track', 'tracks', 'themes', 'sessions']):
            tracks = self.conference_data.get('tracks', [])
            if tracks:
                return "GDTA 2026 conference tracks:\n" + "\n".join([f"• {t}" for t in tracks])
            return "Track information is currently unavailable."

        # Session count
        elif 'how many' in query_lower and 'session' in query_lower:
            count = len(self.sessions_data.get('sessions', []))
            return f"There are {count} sessions scheduled across 2 days."

        # Registration guidance
        elif any(word in query_lower for word in ['register', 'registration', 'sign up', 'signup']):
            return "To register, just type: I want to register. I can guide you through the full registration flow step by step."
        
        # Default
        else:
            return (f"{self.conference_data['description']} "
                   f"It takes place from {self.conference_data['dates']['start']} "
                   f"to {self.conference_data['dates']['end']} "
                   f"in {self.conference_data['location']['city']}.\n\n"
                   f"How can I help you with the conference?")


def is_rag_available() -> bool:
    """Check if RAG can be used (requires API key)"""
    return bool(os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY') or os.getenv('GROK_API_KEY') or os.getenv('OPENAI_API_KEY'))
