"""
Intent Resolver - LLM-based Semantic Understanding Layer

This module provides INTENT CLASSIFICATION ONLY.
The LLM interprets natural language and maps it to predefined intents.

CRITICAL ARCHITECTURAL CONSTRAINTS:
- LLM does NOT make decisions
- LLM does NOT control flow
- LLM does NOT access data
- LLM does NOT generate responses
- Backend remains the single source of truth

If LLM fails, system falls back to keyword matching.
"""

import os
import json
import logging
import re
from enum import Enum
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

# Configure logging
logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """
    Strict enumeration of allowed intents.
    These map directly to backend routing logic.
    """
    GREETING = "greeting"
    CONFERENCE_INFO = "conference_info"
    SCHEDULE_REQUEST = "schedule_request"
    START_REGISTRATION = "start_registration"
    CONTINUE_REGISTRATION = "continue_registration"
    REGISTRATION_STATUS = "registration_status"
    HELP = "help"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    """Result of intent resolution"""
    intent: IntentType
    confidence: float
    fallback_used: bool = False
    error: Optional[str] = None


# System prompt that grounds the LLM
SYSTEM_PROMPT = """You are an intent classification system for the GDTA 2026 Conference Chatbot.

YOUR ONLY JOB: Classify user messages into predefined intents.

ALLOWED INTENTS (STRICT):
- greeting: Hello, hi, hey, good morning
- conference_info: Questions about dates, location, venue, what is GDTA
- schedule_request: Need schedule, plan my day, recommend sessions, show me agenda
- start_registration: Want to register, sign up, enroll, join event
- continue_registration: User is answering registration questions
- registration_status: Check my registration, am I registered
- help: How can you help, what can you do
- unsupported: Requests outside conference scope
- unknown: Cannot determine intent

CRITICAL RULES:
1. Output ONLY valid JSON: {"intent": "<intent>", "confidence": <0.0-1.0>}
2. Never invent features
3. Never make up information
4. Never respond to users directly
5. If unsure, use "unknown" with low confidence

EXAMPLES:
User: "When is the conference?"
Output: {"intent": "conference_info", "confidence": 0.95}

User: "I'd like to sign up please"
Output: {"intent": "start_registration", "confidence": 0.92}

User: "Can you recommend sessions for me?"
Output: {"intent": "schedule_request", "confidence": 0.88}

User: "Hello!"
Output: {"intent": "greeting", "confidence": 0.98}

User: "What's the weather in Paris?"
Output: {"intent": "unsupported", "confidence": 0.85}

User: "asdfkjh"
Output: {"intent": "unknown", "confidence": 0.1}

NEVER deviate from this format.
"""


def _call_openai(user_message: str, api_key: str, timeout: int = 5) -> Optional[Dict]:
    """
    Call OpenAI API for intent classification
    
    Args:
        user_message: User's input text
        api_key: OpenAI API key
        timeout: Request timeout in seconds
    
    Returns:
        Dict with intent and confidence, or None on failure
    """
    try:
        import openai
        
        openai_client = openai.OpenAI(api_key=api_key, timeout=timeout)
        
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,  # Low temperature for consistent classification
            max_tokens=50,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        result = json.loads(content)
        
        # Validate response structure
        if "intent" not in result or "confidence" not in result:
            logger.warning(f"Invalid LLM response structure: {result}")
            return None
        
        # Validate intent is in allowed list
        try:
            IntentType(result["intent"])
        except ValueError:
            logger.warning(f"Invalid intent returned: {result['intent']}")
            return None
        
        # Validate confidence is a number between 0 and 1
        confidence = float(result["confidence"])
        if not 0 <= confidence <= 1:
            logger.warning(f"Invalid confidence value: {confidence}")
            return None
        
        return result
        
    except ImportError:
        logger.warning("OpenAI package not installed")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {e}")
        return None
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return None


def _call_gemini(user_message: str, api_key: str, timeout: int = 5) -> Optional[Dict]:
    """
    Call Google Gemini API for intent classification
    
    Args:
        user_message: User's input text
        api_key: Google API key
        timeout: Request timeout in seconds
    
    Returns:
        Dict with intent and confidence, or None on failure
    """
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"{SYSTEM_PROMPT}\n\nUser message: {user_message}\n\nOutput (JSON only):"
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=50
            )
        )
        
        content = response.text.strip()
        
        # Gemini might wrap JSON in markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        result = json.loads(content)
        
        # Validate response structure
        if "intent" not in result or "confidence" not in result:
            logger.warning(f"Invalid LLM response structure: {result}")
            return None
        
        # Validate intent is in allowed list
        try:
            IntentType(result["intent"])
        except ValueError:
            logger.warning(f"Invalid intent returned: {result['intent']}")
            return None
        
        # Validate confidence
        confidence = float(result["confidence"])
        if not 0 <= confidence <= 1:
            logger.warning(f"Invalid confidence value: {confidence}")
            return None
        
        return result
        
    except ImportError:
        logger.warning("Google Generative AI package not installed")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {e}")
        return None
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return None


def _keyword_fallback(user_message: str) -> Tuple[IntentType, float]:
    """
    Fallback keyword-based intent detection
    
    This is the ORIGINAL logic that must remain as backup.
    
    Args:
        user_message: User's input text (lowercase)
    
    Returns:
        Tuple of (intent, confidence)
    """
    msg_lower = user_message.lower()

    info_keywords = [
        'when', 'where', 'location', 'date', 'what is', 'venue',
        'fee', 'fees', 'price', 'pricing', 'cost', 'charges',
        'safari route', 'safari routes',
        'contact', 'email', 'phone', 'reach',
        'travel', 'stay', 'hotel', 'airport', 'train', 'road',
        'hackathon', 'challenge', 'timeline', 'track', 'tracks'
    ]

    registration_keywords = ['register', 'registration', 'sign up', 'signup', 'enroll', 'join']
    
    # Pattern 1: Registration
    if any(word in msg_lower for word in registration_keywords) and not any(word in msg_lower for word in ['fee', 'fees', 'price', 'pricing', 'cost', 'charges']):
        return IntentType.START_REGISTRATION, 0.85
    
    # Pattern 2: Schedule/Planning
    elif any(word in msg_lower for word in ['schedule', 'plan', 'recommend', 'sessions', 'agenda']):
        return IntentType.SCHEDULE_REQUEST, 0.85
    
    # Pattern 3: Conference Info
    elif any(word in msg_lower for word in info_keywords):
        return IntentType.CONFERENCE_INFO, 0.85
    
    # Pattern 4: Greeting
    elif re.search(r'\b(hello|hi|hey|good morning|good afternoon)\b', msg_lower):
        return IntentType.GREETING, 0.85
    
    # Pattern 5: Help
    elif any(word in msg_lower for word in ['help', 'what can you do', 'how does this work']):
        return IntentType.HELP, 0.85
    
    # Unknown
    else:
        return IntentType.UNKNOWN, 0.3


def resolve_intent(
    user_message: str,
    confidence_threshold: float = 0.6,
    use_llm: bool = True,
    timeout: int = 5
) -> IntentResult:
    """
    Resolve user intent using LLM with keyword fallback
    
    Flow:
    1. Try LLM if enabled and API key available
    2. Validate LLM response
    3. Check confidence threshold
    4. Fall back to keyword matching if needed
    
    Args:
        user_message: User's input text
        confidence_threshold: Minimum confidence to accept LLM result
        use_llm: Whether to attempt LLM call
        timeout: API request timeout in seconds
    
    Returns:
        IntentResult with intent, confidence, and metadata
    """
    
    # Configuration: Check for API keys
    openai_key = os.getenv('OPENAI_API_KEY')
    gemini_key = os.getenv('GOOGLE_API_KEY')
    
    llm_available = bool(openai_key or gemini_key)
    
    # Try LLM if enabled and available
    if use_llm and llm_available:
        llm_result = None
        
        # Try OpenAI first
        if openai_key:
            logger.debug("Attempting OpenAI intent resolution")
            llm_result = _call_openai(user_message, openai_key, timeout)
        
        # Try Gemini if OpenAI failed
        if not llm_result and gemini_key:
            logger.debug("Attempting Gemini intent resolution")
            llm_result = _call_gemini(user_message, gemini_key, timeout)
        
        # If LLM succeeded and confidence is high enough
        if llm_result:
            intent = IntentType(llm_result["intent"])
            confidence = llm_result["confidence"]
            
            if confidence >= confidence_threshold:
                logger.info(f"LLM resolved intent: {intent.value} (confidence: {confidence:.2f})")
                return IntentResult(
                    intent=intent,
                    confidence=confidence,
                    fallback_used=False
                )
            else:
                logger.info(f"LLM confidence too low ({confidence:.2f}), using fallback")
    
    # Fallback to keyword matching
    logger.debug("Using keyword fallback for intent resolution")
    intent, confidence = _keyword_fallback(user_message)
    
    return IntentResult(
        intent=intent,
        confidence=confidence,
        fallback_used=True
    )


def is_llm_available() -> bool:
    """Check if LLM integration is available"""
    return bool(os.getenv('OPENAI_API_KEY') or os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY'))
