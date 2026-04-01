"""
Registration Logic - Deterministic step-based registration flow
This module controls ALL registration decisions - NO AI INVOLVEMENT

ARCHITECTURE:
- Step-based flow (one question at a time)
- Conditional logic (state only if country = India)
- No database writes (stores in session/memory)
- Fully auditable and deterministic
"""

FEE_CONFIG = {
    "Student": {
        "currency": "INR",
        "base": 500,
        "food": 500,
        "safari": 500,
        "fixed": False
    },
    "Academician": {
        "currency": "INR",
        "base": 2000,
        "food": 500,
        "safari": 500,
        "fixed": False
    },
    "Industry People": {
        "currency": "INR",
        "base": 7500,
        "food": 0,
        "safari": 0,
        "fixed": True
    },
    "Foreign Delegate": {
        "currency": "USD",
        "base": 100,
        "food": 0,
        "safari": 0,
        "fixed": True
    }
}

SAFARI_ROUTES = {
    "route 01": "Route 01 - Spiritual Origins & Sacred Landscapes",
    "route 02": "Route 02 - Urban Pulse & Living Heritage",
    "route 03": "Route 03 - Industrial Legacy & Rural Faith"
}


def _format_fee_text(currency, amount):
    if currency == "USD":
        return f"${amount}"
    return f"Rs.{amount}"


def _compute_fee(category, addon_food=False, addon_safari=False):
    if category not in FEE_CONFIG:
        return None

    cfg = FEE_CONFIG[category]
    if cfg["fixed"]:
        addon_food_amount = 0
        addon_safari_amount = 0
    else:
        addon_food_amount = cfg["food"] if addon_food else 0
        addon_safari_amount = cfg["safari"] if addon_safari else 0

    total = cfg["base"] + addon_food_amount + addon_safari_amount
    return {
        "currency": cfg["currency"],
        "base": cfg["base"],
        "addon_food_accommodation_fee": addon_food_amount,
        "addon_safari_fee": addon_safari_amount,
        "total_fee": total,
        "fixed_all_inclusive": cfg["fixed"]
    }


class RegistrationSteps:
    """Registration step constants"""
    CONSENT = "consent"
    NAME = "name"
    INSTITUTION = "institution"
    ROLE = "role"
    REGISTRATION_CATEGORY = "registration_category"
    ADDON_FOOD_ACCOMMODATION = "addon_food_accommodation"
    ADDON_SAFARI = "addon_safari"
    SAFARI_ROUTE = "safari_route"
    GDTA_MEMBER = "gdta_member"
    GDTA_AFFILIATION = "gdta_affiliation"
    COUNTRY = "country"
    STATE = "state"
    EMAIL = "email"
    REVIEW = "review"
    CONFIRMATION = "confirmation"
    COMPLETED = "completed"


class RegistrationState:
    """
    Manages registration state for a user session
    
    This is stored in session or memory (no database yet)
    """
    
    def __init__(self):
        self.current_step = RegistrationSteps.CONSENT
        self.data = {
            "consent": None,
            "name": None,
            "institution": None,
            "role": None,
            "registration_category": None,
            "addon_food_accommodation": "No",
            "addon_safari": "No",
            "safari_route": None,
            "gdta_member": None,
            "gdta_affiliation": None,
            "country": None,
            "state": None,
            "email": None
        }
        self.editing_field = None
        self.is_active = True
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "current_step": self.current_step,
            "data": self.data,
            "is_active": self.is_active
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary (from session)"""
        state = cls()
        state.current_step = data.get("current_step", RegistrationSteps.CONSENT)
        state.data = data.get("data", {
            "consent": None,
            "name": None,
            "institution": None,
            "role": None,
            "registration_category": None,
            "addon_food_accommodation": "No",
            "addon_safari": "No",
            "safari_route": None,
            "gdta_member": None,
            "gdta_affiliation": None,
            "country": None,
            "state": None,
            "email": None
        })
        state.editing_field = data.get("editing_field", None)
        state.is_active = data.get("is_active", True)
        return state


def start_registration():
    """
    Initialize a new registration session
    
    Returns:
        RegistrationState object
    """
    return RegistrationState()


def get_current_question(registration_state):
    """
    Get the question for the current step
    
    DETERMINISTIC: Returns exact question text based on current step
    NO AI involvement in question generation
    
    Args:
        registration_state: RegistrationState object
    
    Returns:
        dict with question text and metadata
    """
    step = registration_state.current_step
    
    questions = {
        RegistrationSteps.CONSENT: {
            "question": "Do you consent to your data being used for GDTA 2026 conference communication?",
            "options": ["Yes", "No"],
            "field": "consent",
            "validation_type": "options"
        },
        RegistrationSteps.NAME: {
            "question": "What is your full name?",
            "options": None,
            "field": "name",
            "validation_type": "free_text"
        },
        RegistrationSteps.INSTITUTION: {
            "question": "What is your institution name?",
            "options": None,
            "field": "institution",
            "validation_type": "free_text"
        },
        RegistrationSteps.ROLE: {
            "question": "What is your role?",
            "options": ["Student", "Industry", "Faculty"],
            "field": "role",
            "validation_type": "options"
        },
        RegistrationSteps.REGISTRATION_CATEGORY: {
            "question": "Please choose your registration category.",
            "options": ["Student", "Academician", "Industry People", "Foreign Delegate"],
            "field": "registration_category",
            "validation_type": "options"
        },
        RegistrationSteps.ADDON_FOOD_ACCOMMODATION: {
            "question": "Would you like to add Food & Accommodation?",
            "options": ["Yes", "No"],
            "field": "addon_food_accommodation",
            "validation_type": "options"
        },
        RegistrationSteps.ADDON_SAFARI: {
            "question": "Would you like to add Safari?",
            "options": ["Yes", "No"],
            "field": "addon_safari",
            "validation_type": "options"
        },
        RegistrationSteps.SAFARI_ROUTE: {
            "question": "Please select one safari route.",
            "options": [
                "Route 01 - Spiritual Origins & Sacred Landscapes",
                "Route 02 - Urban Pulse & Living Heritage",
                "Route 03 - Industrial Legacy & Rural Faith"
            ],
            "field": "safari_route",
            "validation_type": "options"
        },
        RegistrationSteps.GDTA_MEMBER: {
            "question": "Are you a GDTA member?",
            "options": ["Yes", "No"],
            "field": "gdta_member",
            "validation_type": "options"
        },
        RegistrationSteps.GDTA_AFFILIATION: {
            "question": "Is your institution affiliated with GDTA or participating as a GDTA partner?",
            "options": ["Yes", "No", "Not sure"],
            "field": "gdta_affiliation",
            "validation_type": "options"
        },
        RegistrationSteps.COUNTRY: {
            "question": "Which country are you travelling from?",
            "options": None,
            "field": "country",
            "validation_type": "free_text"
        },
        RegistrationSteps.STATE: {
            "question": "Which state are you travelling from?",
            "options": None,
            "field": "state",
            "validation_type": "free_text"
        },
        RegistrationSteps.EMAIL: {
            "question": "What is your email address?",
            "options": None,
            "field": "email",
            "validation_type": "email"
        },
        RegistrationSteps.REVIEW: {
            "question": "Please review your details. Type the field name to edit (name, institution, role, registration_category, addon_food_accommodation, addon_safari, safari_route, gdta_member, gdta_affiliation, country, state, email) or type CONTINUE to proceed.",
            "options": None,
            "field": None,
            "validation_type": "review"
        },
        RegistrationSteps.CONFIRMATION: {
            "question": "Please review your registration details",
            "options": ["CONFIRM", "EDIT"],
            "field": None,
            "validation_type": "confirmation"
        }
    }
    
    return questions.get(step, None)


def validate_input(user_input, current_step):
    """
    Validate user input for current step
    
    DETERMINISTIC VALIDATION RULES:
    - Consent: Must be Yes/No (case-insensitive)
    - Name: Non-empty, minimum 2 characters
    - Institution: Non-empty, minimum 2 characters
    - Role: Must be Student/Industry/Faculty
    - GDTA Member: Must be Yes/No
    - GDTA affiliation: Must be Yes/No/Not sure (case-insensitive)
    - Country: Any non-empty text
    - State: Any non-empty text
    - Email: Must match email regex pattern
    - Confirmation: Must be CONFIRM or EDIT (case-insensitive)
    
    Args:
        user_input: User's input string
        current_step: Current registration step
    
    Returns:
        (is_valid, normalized_value, error_message)
    """
    import re
    
    user_input = user_input.strip()
    
    if not user_input:
        return False, None, "Please provide an answer."
    
    if current_step == RegistrationSteps.CONSENT:
        # Must be Yes or No
        normalized = user_input.lower()
        if normalized in ["yes", "y", "i agree", "agree"]:
            return True, "Yes", None
        elif normalized in ["no", "n", "decline"]:
            return True, "No", None
        else:
            return False, None, "Invalid response. Please answer 'Yes' or 'No' to the consent question."
    
    elif current_step == RegistrationSteps.NAME:
        # Any non-empty text, minimum 2 characters
        if len(user_input) < 2:
            return False, None, "Please provide a valid name."
        return True, user_input.title(), None
    
    elif current_step == RegistrationSteps.INSTITUTION:
        # Any non-empty text, minimum 2 characters
        if len(user_input) < 2:
            return False, None, "Please provide a valid institution name."
        return True, user_input.title(), None
    
    elif current_step == RegistrationSteps.ROLE:
        # Must be Student, Industry, or Faculty
        normalized = user_input.lower()
        if normalized in ["student", "students"]:
            return True, "Student", None
        elif normalized in ["industry", "professional"]:
            return True, "Industry", None
        elif normalized in ["faculty", "teacher", "professor"]:
            return True, "Faculty", None
        else:
            return False, None, "Please choose: Student, Industry, or Faculty."

    elif current_step == RegistrationSteps.REGISTRATION_CATEGORY:
        normalized = user_input.lower().strip()
        if normalized in ["student", "students"]:
            return True, "Student", None
        elif normalized in ["academician", "academic", "academics", "faculty"]:
            return True, "Academician", None
        elif normalized in ["industry people", "industrial people", "industry", "industrial", "industry professional"]:
            return True, "Industry People", None
        elif normalized in ["foreign delegate", "foreign delegates", "foreign", "international delegate"]:
            return True, "Foreign Delegate", None
        else:
            return False, None, "Please choose: Student, Academician, Industry People, or Foreign Delegate."

    elif current_step == RegistrationSteps.ADDON_FOOD_ACCOMMODATION:
        normalized = user_input.lower()
        if normalized in ["yes", "y"]:
            return True, "Yes", None
        elif normalized in ["no", "n"]:
            return True, "No", None
        else:
            return False, None, "Invalid response. Please answer 'Yes' or 'No'."

    elif current_step == RegistrationSteps.ADDON_SAFARI:
        normalized = user_input.lower()
        if normalized in ["yes", "y"]:
            return True, "Yes", None
        elif normalized in ["no", "n"]:
            return True, "No", None
        else:
            return False, None, "Invalid response. Please answer 'Yes' or 'No'."

    elif current_step == RegistrationSteps.SAFARI_ROUTE:
        normalized = user_input.lower().strip()
        if normalized in ["route 01", "route 1", "1", "01"]:
            return True, SAFARI_ROUTES["route 01"], None
        elif normalized in ["route 02", "route 2", "2", "02"]:
            return True, SAFARI_ROUTES["route 02"], None
        elif normalized in ["route 03", "route 3", "3", "03"]:
            return True, SAFARI_ROUTES["route 03"], None
        elif normalized in [route.lower() for route in SAFARI_ROUTES.values()]:
            # exact route name entered by user
            for route_name in SAFARI_ROUTES.values():
                if normalized == route_name.lower():
                    return True, route_name, None
        return False, None, "Please choose Route 01, Route 02, or Route 03."
    
    elif current_step == RegistrationSteps.GDTA_MEMBER:
        # Must be Yes or No
        normalized = user_input.lower()
        if normalized in ["yes", "y"]:
            return True, "Yes", None
        elif normalized in ["no", "n"]:
            return True, "No", None
        else:
            return False, None, "Invalid response. Please answer 'Yes' or 'No'."
    
    elif current_step == RegistrationSteps.GDTA_AFFILIATION:
        # Must be one of the three options
        normalized = user_input.lower()
        if normalized in ["yes", "y"]:
            return True, "Yes", None
        elif normalized in ["no", "n"]:
            return True, "No", None
        elif normalized in ["not sure", "notsure", "unsure", "not_sure"]:
            return True, "Not sure", None
        else:
            return False, None, "Please answer: Yes, No, or Not sure."
    
    elif current_step == RegistrationSteps.COUNTRY:
        # Any non-empty text
        if len(user_input) < 2:
            return False, None, "Please provide a valid country name."
        return True, user_input.title(), None
    
    elif current_step == RegistrationSteps.STATE:
        # Any non-empty text
        if len(user_input) < 2:
            return False, None, "Please provide a valid state name."
        return True, user_input.title(), None
    
    elif current_step == RegistrationSteps.EMAIL:
        # Email validation using regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, user_input):
            return False, None, "Please provide a valid email address."
        # Store email in lowercase for consistency
        return True, user_input.lower(), None
    
    elif current_step == RegistrationSteps.REVIEW:
        # Can be field name or CONTINUE
        normalized = user_input.lower().strip()
        valid_fields = [
            "name", "institution", "role", "registration_category", "addon_food_accommodation",
            "addon_safari", "safari_route", "gdta_member", "gdta_affiliation", "country", "state",
            "email", "continue", "c"
        ]
        if normalized in valid_fields:
            return True, normalized, None
        else:
            return False, None, "Please type a field name to edit (name, institution, role, registration_category, addon_food_accommodation, addon_safari, safari_route, gdta_member, gdta_affiliation, country, state, email) or CONTINUE."
    
    elif current_step == RegistrationSteps.CONFIRMATION:
        normalized = user_input.lower()
        if normalized in ["confirm", "yes", "y"]:
            return True, "CONFIRM", None
        elif normalized in ["edit", "change", "no", "n"]:
            return True, "EDIT", None
        else:
            return False, None, "Please type CONFIRM to proceed or EDIT to change your details."
    
    return False, None, "Invalid input."


def process_input(registration_state, user_input):
    """
    Process user input and advance to next step
    
    DETERMINISTIC LOGIC:
    1. Validate input for current step
    2. Store validated data
    3. Determine next step based on rules
    4. Update state
    
    Args:
        registration_state: RegistrationState object
        user_input: User's input string
    
    Returns:
        dict with:
        - success: bool
        - message: str (response to user)
        - next_question: dict or None
        - completed: bool
    """
    current_step = registration_state.current_step
    
    # Validate input
    is_valid, normalized_value, error_message = validate_input(user_input, current_step)
    
    if not is_valid:
        return {
            "success": False,
            "message": error_message,
            "next_question": get_current_question(registration_state),
            "completed": False,
            "state": registration_state.to_dict()
        }
    
    # Store validated data
    if current_step == RegistrationSteps.CONSENT:
        registration_state.data["consent"] = normalized_value
        
        # If user declines consent, terminate registration
        if normalized_value == "No":
            registration_state.is_active = False
            registration_state.current_step = RegistrationSteps.COMPLETED
            
            return {
                "success": True,
                "message": "Registration cancelled. You must consent to data usage to complete registration.",
                "next_question": None,
                "completed": False,
                "cancelled": True,
                "state": registration_state.to_dict()
            }
        
        # User consented, proceed to NAME
        registration_state.current_step = RegistrationSteps.NAME
        
        return {
            "success": True,
            "message": "Thank you for your consent. Let's begin registration.",
            "next_question": get_current_question(registration_state),
            "completed": False,
            "state": registration_state.to_dict()
        }
    
    elif current_step == RegistrationSteps.NAME:
        registration_state.data["name"] = normalized_value
        
        # If editing, return to REVIEW
        if registration_state.editing_field:
            registration_state.current_step = RegistrationSteps.REVIEW
            registration_state.editing_field = None
            message = f"Name updated to: {normalized_value}"
        else:
            registration_state.current_step = RegistrationSteps.INSTITUTION
            message = f"Thank you, {normalized_value}."
        
        return {
            "success": True,
            "message": message,
            "next_question": get_current_question(registration_state),
            "completed": False,
            "state": registration_state.to_dict()
        }
    
    elif current_step == RegistrationSteps.INSTITUTION:
        registration_state.data["institution"] = normalized_value
        
        # If editing, return to REVIEW
        if registration_state.editing_field:
            registration_state.current_step = RegistrationSteps.REVIEW
            registration_state.editing_field = None
            message = f"Institution updated to: {normalized_value}"
        else:
            registration_state.current_step = RegistrationSteps.ROLE
            message = f"Institution recorded: {normalized_value}"
        
        return {
            "success": True,
            "message": message,
            "next_question": get_current_question(registration_state),
            "completed": False,
            "state": registration_state.to_dict()
        }
    
    elif current_step == RegistrationSteps.ROLE:
        registration_state.data["role"] = normalized_value
        
        # If editing, return to REVIEW
        if registration_state.editing_field:
            registration_state.current_step = RegistrationSteps.REVIEW
            registration_state.editing_field = None
            message = f"Role updated to: {normalized_value}"
        else:
            registration_state.current_step = RegistrationSteps.REGISTRATION_CATEGORY
            message = f"Role recorded: {normalized_value}"
        
        return {
            "success": True,
            "message": message,
            "next_question": get_current_question(registration_state),
            "completed": False,
            "state": registration_state.to_dict()
        }

    elif current_step == RegistrationSteps.REGISTRATION_CATEGORY:
        registration_state.data["registration_category"] = normalized_value

        # Reset dependent fields when category changes
        registration_state.data["addon_food_accommodation"] = "No"
        registration_state.data["addon_safari"] = "No"
        registration_state.data["safari_route"] = None

        fee_cfg = FEE_CONFIG.get(normalized_value, {})
        is_fixed = fee_cfg.get("fixed", False)

        if registration_state.editing_field:
            registration_state.current_step = RegistrationSteps.REVIEW
            registration_state.editing_field = None
            message = f"Registration category updated to: {normalized_value}"
        else:
            registration_state.current_step = RegistrationSteps.GDTA_MEMBER if is_fixed else RegistrationSteps.ADDON_FOOD_ACCOMMODATION
            message = f"Registration category recorded: {normalized_value}"

        return {
            "success": True,
            "message": message,
            "next_question": get_current_question(registration_state),
            "completed": False,
            "state": registration_state.to_dict()
        }

    elif current_step == RegistrationSteps.ADDON_FOOD_ACCOMMODATION:
        registration_state.data["addon_food_accommodation"] = normalized_value

        if registration_state.editing_field:
            registration_state.current_step = RegistrationSteps.REVIEW
            registration_state.editing_field = None
            message = f"Food & Accommodation add-on updated to: {normalized_value}"
        else:
            registration_state.current_step = RegistrationSteps.ADDON_SAFARI
            message = f"Food & Accommodation add-on: {normalized_value}"

        return {
            "success": True,
            "message": message,
            "next_question": get_current_question(registration_state),
            "completed": False,
            "state": registration_state.to_dict()
        }

    elif current_step == RegistrationSteps.ADDON_SAFARI:
        registration_state.data["addon_safari"] = normalized_value

        if normalized_value != "Yes":
            registration_state.data["safari_route"] = None

        if registration_state.editing_field:
            registration_state.current_step = RegistrationSteps.REVIEW
            registration_state.editing_field = None
            message = f"Safari add-on updated to: {normalized_value}"
        else:
            registration_state.current_step = RegistrationSteps.SAFARI_ROUTE if normalized_value == "Yes" else RegistrationSteps.GDTA_MEMBER
            message = f"Safari add-on: {normalized_value}"

        return {
            "success": True,
            "message": message,
            "next_question": get_current_question(registration_state),
            "completed": False,
            "state": registration_state.to_dict()
        }

    elif current_step == RegistrationSteps.SAFARI_ROUTE:
        registration_state.data["safari_route"] = normalized_value

        if registration_state.editing_field:
            registration_state.current_step = RegistrationSteps.REVIEW
            registration_state.editing_field = None
            message = f"Safari route updated to: {normalized_value}"
        else:
            registration_state.current_step = RegistrationSteps.GDTA_MEMBER
            message = f"Safari route selected: {normalized_value}"

        return {
            "success": True,
            "message": message,
            "next_question": get_current_question(registration_state),
            "completed": False,
            "state": registration_state.to_dict()
        }
    
    elif current_step == RegistrationSteps.GDTA_MEMBER:
        registration_state.data["gdta_member"] = normalized_value
        
        # If editing, return to REVIEW
        if registration_state.editing_field:
            registration_state.current_step = RegistrationSteps.REVIEW
            registration_state.editing_field = None
            message = f"GDTA Member updated to: {normalized_value}"
        else:
            registration_state.current_step = RegistrationSteps.GDTA_AFFILIATION
            message = f"GDTA Member: {normalized_value}"
        
        return {
            "success": True,
            "message": message,
            "next_question": get_current_question(registration_state),
            "completed": False,
            "state": registration_state.to_dict()
        }
    
    elif current_step == RegistrationSteps.GDTA_AFFILIATION:
        registration_state.data["gdta_affiliation"] = normalized_value
        
        # If editing, return to REVIEW
        if registration_state.editing_field:
            registration_state.current_step = RegistrationSteps.REVIEW
            registration_state.editing_field = None
            message = f"GDTA affiliation updated to: {normalized_value}"
        else:
            registration_state.current_step = RegistrationSteps.COUNTRY
            message = f"Thank you. Your GDTA affiliation: {normalized_value}"
        
        return {
            "success": True,
            "message": message,
            "next_question": get_current_question(registration_state),
            "completed": False,
            "state": registration_state.to_dict()
        }
    
    elif current_step == RegistrationSteps.COUNTRY:
        old_country = registration_state.data.get("country")
        old_country_lower = old_country.lower() if old_country else ""
        registration_state.data["country"] = normalized_value
        
        # TC-14 FIX: Auto-clear state if changing from India to non-India
        if old_country_lower == "india" and normalized_value.lower() != "india":
            registration_state.data["state"] = None
        
        # If editing, return to REVIEW
        if registration_state.editing_field:
            registration_state.current_step = RegistrationSteps.REVIEW
            registration_state.editing_field = None
            message = f"Country updated to: {normalized_value}"
        else:
            # CONDITIONAL LOGIC: Ask for state only if country is India
            if normalized_value.lower() == "india":
                registration_state.current_step = RegistrationSteps.STATE
            else:
                # Skip state question, set to null
                registration_state.data["state"] = None
                registration_state.current_step = RegistrationSteps.EMAIL
            message = f"Country recorded: {normalized_value}"
        
        return {
            "success": True,
            "message": message,
            "next_question": get_current_question(registration_state),
            "completed": False,
            "state": registration_state.to_dict()
        }
    
    elif current_step == RegistrationSteps.STATE:
        registration_state.data["state"] = normalized_value
        
        # After state, go to EMAIL (or REVIEW if editing)
        if registration_state.editing_field:
            registration_state.current_step = RegistrationSteps.REVIEW
            registration_state.editing_field = None
            message = f"State updated to: {normalized_value}"
        else:
            registration_state.current_step = RegistrationSteps.EMAIL
            message = f"State recorded: {normalized_value}"
        
        return {
            "success": True,
            "message": message,
            "next_question": get_current_question(registration_state),
            "completed": False,
            "state": registration_state.to_dict()
        }
    
    elif current_step == RegistrationSteps.EMAIL:
        registration_state.data["email"] = normalized_value
        
        # TODO: Check for duplicate email when database is available
        # For now, proceed to REVIEW
        
        # If editing, return to REVIEW
        if registration_state.editing_field:
            registration_state.current_step = RegistrationSteps.REVIEW
            registration_state.editing_field = None
            message = f"Email updated to: {normalized_value}\n\nPlease review all your details below:"
        else:
            registration_state.current_step = RegistrationSteps.REVIEW
            message = f"Email recorded: {normalized_value}\n\nPlease review all your details below:"
        
        return {
            "success": True,
            "message": message,
            "next_question": get_current_question(registration_state),
            "completed": False,
            "state": registration_state.to_dict()
        }
    
    elif current_step == RegistrationSteps.REVIEW:
        # Handle review/edit logic
        if normalized_value in ["continue", "c"]:
            # Move to confirmation
            registration_state.current_step = RegistrationSteps.CONFIRMATION
            return {
                "success": True,
                "message": "All details confirmed.",
                "next_question": get_current_question(registration_state),
                "completed": False,
                "state": registration_state.to_dict()
            }
        else:
            # User wants to edit a field
            field_to_step = {
                "name": RegistrationSteps.NAME,
                "institution": RegistrationSteps.INSTITUTION,
                "role": RegistrationSteps.ROLE,
                "registration_category": RegistrationSteps.REGISTRATION_CATEGORY,
                "addon_food_accommodation": RegistrationSteps.ADDON_FOOD_ACCOMMODATION,
                "addon_safari": RegistrationSteps.ADDON_SAFARI,
                "safari_route": RegistrationSteps.SAFARI_ROUTE,
                "gdta_member": RegistrationSteps.GDTA_MEMBER,
                "gdta_affiliation": RegistrationSteps.GDTA_AFFILIATION,
                "country": RegistrationSteps.COUNTRY,
                "state": RegistrationSteps.STATE,
                "email": RegistrationSteps.EMAIL
            }
            
            if normalized_value in field_to_step:
                registration_state.current_step = field_to_step[normalized_value]
                registration_state.editing_field = normalized_value
                
                return {
                    "success": True,
                    "message": f"Editing {normalized_value}. Please provide new value.",
                    "next_question": get_current_question(registration_state),
                    "completed": False,
                    "state": registration_state.to_dict()
                }
            else:
                return {
                    "success": False,
                    "message": "Invalid field name. Valid fields: name, institution, role, registration_category, addon_food_accommodation, addon_safari, safari_route, gdta_member, gdta_affiliation, country, state, email. Or type 'continue' to proceed.",
                    "next_question": get_current_question(registration_state),
                    "completed": False,
                    "state": registration_state.to_dict()
                }
    
    elif current_step == RegistrationSteps.CONFIRMATION:
        if normalized_value == "CONFIRM":
            # Submit registration to backend
            submission_result = submit_registration(registration_state.data)
            
            if submission_result["success"]:
                # Complete registration
                registration_state.current_step = RegistrationSteps.COMPLETED
                registration_state.is_active = False
                
                return {
                    "success": True,
                    "message": submission_result["message"],
                    "next_question": None,
                    "completed": True,
                    "state": registration_state.to_dict()
                }
            else:
                # Backend rejected submission
                return {
                    "success": False,
                    "message": submission_result["message"],
                    "error_code": submission_result.get("error_code"),
                    "next_question": get_current_question(registration_state),
                    "completed": False,
                    "state": registration_state.to_dict()
                }
        else:  # EDIT
            # Go back to REVIEW to allow editing specific fields
            registration_state.current_step = RegistrationSteps.REVIEW
            
            return {
                "success": True,
                "message": "You can now edit any field. Type the field name (name, institution, role, registration_category, addon_food_accommodation, addon_safari, safari_route, gdta_member, gdta_affiliation, country, state, email) or CONTINUE to proceed.",
                "next_question": get_current_question(registration_state),
                "completed": False,
                "state": registration_state.to_dict()
            }
    
    return {
        "success": False,
        "message": "An error occurred. Please try again.",
        "next_question": get_current_question(registration_state),
        "completed": False,
        "state": registration_state.to_dict()
    }


def get_summary(registration_state):
    """
    Generate a summary of collected registration data
    
    Used at confirmation step
    
    Args:
        registration_state: RegistrationState object
    
    Returns:
        Formatted string with all collected data
    """
    data = registration_state.data
    
    lines = [
        "Registration Details:",
        f"Name: {data.get('name', 'Not provided')}",
        f"Institution: {data.get('institution', 'Not provided')}",
        f"Role: {data.get('role', 'Not provided')}",
        f"Registration Category: {data.get('registration_category', 'Not provided')}",
        f"Food & Accommodation Add-on: {data.get('addon_food_accommodation', 'No')}",
        f"Safari Add-on: {data.get('addon_safari', 'No')}",
        f"GDTA Member: {data.get('gdta_member', 'Not provided')}",
        f"GDTA Affiliation: {data.get('gdta_affiliation', 'Not provided')}",
        f"Country: {data.get('country', 'Not provided')}"
    ]

    if data.get('addon_safari') == 'Yes':
        lines.append(f"Safari Route: {data.get('safari_route', 'Not selected')}")
    
    # Only show state if it was collected
    if data.get('state'):
        lines.append(f"State: {data['state']}")
    
    # Add email
    lines.append(f"Email: {data.get('email', 'Not provided')}")

    # Add computed fee summary if category is present
    category = data.get('registration_category')
    if category:
        addon_food = str(data.get('addon_food_accommodation', 'No')).strip().lower() == 'yes'
        addon_safari = str(data.get('addon_safari', 'No')).strip().lower() == 'yes'
        fee_breakdown = _compute_fee(category, addon_food=addon_food, addon_safari=addon_safari)
        if fee_breakdown:
            lines.append(
                f"Final Fee: {_format_fee_text(fee_breakdown['currency'], fee_breakdown['total_fee'])}"
                f"{' (All inclusive)' if fee_breakdown['fixed_all_inclusive'] else ''}"
            )
    
    lines.append("")
    lines.append("Type CONFIRM to proceed or EDIT to change your details.")
    
    return "\n".join(lines)


def cancel_registration(registration_state):
    """
    Cancel the registration process
    
    Args:
        registration_state: RegistrationState object
    
    Returns:
        dict with cancellation confirmation
    """
    registration_state.is_active = False
    registration_state.current_step = None
    
    return {
        "success": True,
        "message": "Registration cancelled. How else can I assist you?",
        "cancelled": True
    }


def check_duplicate_email(email):
    """
    Check if email already exists in database
    
    EXTENSIBLE DESIGN:
    - Queries Firebase Firestore for existing email
    - Backend logic controls duplicate checking, NOT AI
    
    Args:
        email: Email address to check
    
    Returns:
        bool: True if duplicate found, False otherwise
    """
    try:
        from db.firebase_models import Registration
        
        existing = Registration.get_by_email(email)
        return existing is not None
    except Exception as e:
        print(f"Error checking duplicate email: {e}")
        # If database check fails, assume no duplicate to not block registration
        return False


def is_registration_open():
    """
    Check if registration is currently open
    
    BACKEND CONTROLLED:
    - Checks system configuration/database for registration status
    - Can be toggled by admin without code changes
    - Returns deterministic status
    
    Returns:
        tuple: (is_open: bool, message: str)
    """
    # TODO: Check database or config file for registration status
    # For now, always open
    return True, None


def submit_registration(registration_data):
    """
    Submit registration to backend/database
    
    BACKEND CONTROLLED SUBMISSION:
    - Validates all required fields are present
    - Checks for duplicate email
    - Writes to database (when available)
    - Returns explicit success/failure status
    
    Args:
        registration_data: dict with all registration fields
    
    Returns:
        dict with:
        - success: bool
        - message: str
        - error_code: str (if failed)
    """
    try:
        # Check if registration is open
        is_open, message = is_registration_open()
        if not is_open:
            return {
                "success": False,
                "message": message or "Registration is currently closed.",
                "error_code": "REGISTRATION_CLOSED"
            }
        
        # Validate required fields. Role is optional for direct web form registrations.
        registration_source = (registration_data.get("registration_source") or "").strip().lower()
        required_fields = [
            "consent", "name", "institution", "registration_category",
            "gdta_member", "gdta_affiliation", "country", "email"
        ]

        if registration_source != "form":
            required_fields.append("role")
        
        for field in required_fields:
            if not registration_data.get(field):
                return {
                    "success": False,
                    "message": f"Missing required field: {field}",
                    "error_code": "MISSING_FIELD"
                }
        
        # Check consent
        if registration_data.get("consent") != "Yes":
            return {
                "success": False,
                "message": "Registration requires consent to data usage.",
                "error_code": "CONSENT_REQUIRED"
            }
        
        # Check duplicate email
        if check_duplicate_email(registration_data.get("email")):
            return {
                "success": False,
                "message": "This email address is already registered.",
                "error_code": "DUPLICATE_EMAIL"
            }

        # Validate and compute fee breakdown for form registrations
        registration_category = registration_data.get("registration_category")
        if registration_category:
            addon_food = str(registration_data.get("addon_food_accommodation", "No")).strip().lower() in ["yes", "true", "1"]
            addon_safari = str(registration_data.get("addon_safari", "No")).strip().lower() in ["yes", "true", "1"]
            fee_breakdown = _compute_fee(registration_category, addon_food=addon_food, addon_safari=addon_safari)

            if not fee_breakdown:
                return {
                    "success": False,
                    "message": "Invalid registration category selected.",
                    "error_code": "INVALID_CATEGORY"
                }

            if addon_safari and not str(registration_data.get("safari_route", "")).strip():
                return {
                    "success": False,
                    "message": "Safari route is required when safari add-on is selected.",
                    "error_code": "MISSING_SAFARI_ROUTE"
                }

            if not addon_safari:
                registration_data["safari_route"] = None

            registration_data["fee_currency"] = fee_breakdown["currency"]
            registration_data["base_fee"] = fee_breakdown["base"]
            registration_data["addon_food_accommodation_fee"] = fee_breakdown["addon_food_accommodation_fee"]
            registration_data["addon_safari_fee"] = fee_breakdown["addon_safari_fee"]
            registration_data["total_fee"] = fee_breakdown["total_fee"]
            registration_data["fixed_all_inclusive"] = fee_breakdown["fixed_all_inclusive"]
        
        # Save to Firebase Firestore
        try:
            from db.firebase_models import Registration
            
            # Create new registration record
            # Note: Using default event_id for GDTA 2026
            role_value = registration_data.get("role") or "Not specified"

            new_registration = Registration(
                event_id='gdta-2026',  # Default event ID
                name=registration_data.get("name"),
                email=registration_data.get("email"),
                institution=registration_data.get("institution"),
                role=role_value,
                gdta_member=registration_data.get("gdta_member"),
                gdta_affiliation=registration_data.get("gdta_affiliation"),
                country=registration_data.get("country"),
                state=registration_data.get("state"),
                consent=registration_data.get("consent"),
                registration_source=registration_data.get("registration_source", "chatbot"),
                session_id=registration_data.get("session_id"),
                registration_category=registration_data.get("registration_category"),
                addon_food_accommodation=registration_data.get("addon_food_accommodation"),
                addon_safari=registration_data.get("addon_safari"),
                safari_route=registration_data.get("safari_route"),
                fee_currency=registration_data.get("fee_currency"),
                base_fee=registration_data.get("base_fee"),
                addon_food_accommodation_fee=registration_data.get("addon_food_accommodation_fee"),
                addon_safari_fee=registration_data.get("addon_safari_fee"),
                total_fee=registration_data.get("total_fee"),
                fixed_all_inclusive=registration_data.get("fixed_all_inclusive"),
                status='pending'
            )
            
            registration_id = new_registration.save()
            
            print(f"✓ Registration saved to Firebase: ID={registration_id}, Email={registration_data.get('email')}")

            fee_display_text = None
            if registration_data.get("fee_currency") and registration_data.get("total_fee") is not None:
                fee_display_text = _format_fee_text(registration_data.get("fee_currency"), registration_data.get("total_fee"))
            
            return {
                "success": True,
                "message": "Registration submitted successfully. Your details have been recorded.",
                "registration_id": registration_id,
                "fee_display_text": fee_display_text,
                "total_fee": registration_data.get("total_fee"),
                "fee_currency": registration_data.get("fee_currency")
            }
            
        except Exception as db_error:
            print(f"Database error: {db_error}")
            # Fallback - even if DB fails, acknowledge registration
            return {
                "success": True,
                "message": "Registration received. Our team will contact you shortly.",
                "registration_id": None,
                "fee_display_text": _format_fee_text(registration_data.get("fee_currency"), registration_data.get("total_fee")) if registration_data.get("fee_currency") and registration_data.get("total_fee") is not None else None,
                "total_fee": registration_data.get("total_fee"),
                "fee_currency": registration_data.get("fee_currency")
            }
        
    except Exception as e:
        # Backend error handling - never expose internal errors
        print(f"Registration error: {e}")
        return {
            "success": False,
            "message": "An error occurred during registration. Please try again later.",
            "error_code": "SERVER_ERROR"
        }
