import uuid
import re
from datetime import datetime
from typing import Dict, Tuple

from chatbot.nlu import gemini_match_choice
from chatbot.rag import answer_query as rag_answer_query
from core.constants import ERROR_CODES
from core.exceptions import AppError
from registrations.services import submit_registration
from registrations.state_machine import FEE_CONFIG, SAFARI_ROUTES
from services.firebase.firestore import create_document, get_document, query_documents, update_document
from services.payments.zoho import create_payment_link

CHATBOT_SESSIONS_COLLECTION = "chatbot_sessions"
HACKATHON_COLLECTION = "hackathon_registrations"
CONFERENCE_EVENT_ID = "gdta-2026"

FIXED_FEE_CATEGORIES = {k for k, v in FEE_CONFIG.items() if v.get("fixed")}
HACKATHON_TRACKS = {"Healthcare", "Education Transformation", "Smart City & Infrastructure"}
ROUTE_CHOICES = {
    "Route 01": SAFARI_ROUTES["route 01"],
    "Route 02": SAFARI_ROUTES["route 02"],
    "Route 03": SAFARI_ROUTES["route 03"],
}


def _ts() -> str:
    return datetime.utcnow().isoformat()


def _yes(value: str) -> bool:
    return str(value or "").strip().lower() in {"yes", "y", "true", "1"}


def _contains_phrase(raw_text: str, phrase: str) -> bool:
    text = re.sub(r"\s+", " ", str(raw_text or "").strip().lower())
    p = re.sub(r"\s+", " ", str(phrase or "").strip().lower())
    if not text or not p:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(p)}(?![a-z0-9])", text) is not None


def _normalize_yes_no(value: str, *, context: str = "") -> bool:
    raw = str(value or "").strip().lower()
    yes_values = {
        "yes",
        "y",
        "true",
        "1",
        "ok",
        "okay",
        "sure",
        "yeah",
        "yep",
        "please do",
        "go ahead",
        "sounds good",
        "of course",
        "let's do it",
        "lets do it",
        "i agree",
        "please proceed",
        "proceed",
        "continue",
    }
    no_values = {
        "no",
        "n",
        "false",
        "0",
        "nope",
        "nah",
        "stop",
        "don't",
        "dont",
        "no thanks",
        "not now",
        "skip",
        "pass",
        "decline",
        "maybe later",
        "not interested",
    }

    if raw in yes_values:
        return True
    if raw in no_values:
        return False

    positive_hit = any(_contains_phrase(raw, token) for token in yes_values)
    negative_hit = any(_contains_phrase(raw, token) for token in no_values)

    if positive_hit and not negative_hit:
        return True
    if negative_hit and not positive_hit:
        return False

    llm = gemini_match_choice(
        user_text=value,
        options=["Yes", "No"],
        task_hint=f"Classify yes/no intent for chatbot step: {context}",
    )
    if llm == "Yes":
        return True
    if llm == "No":
        return False

    raise AppError("Please reply with Yes or No.", ERROR_CODES["VALIDATION_ERROR"], 400)


def _is_confirm_command(value: str, *, keyword: str, context: str) -> bool:
    raw = str(value or "").strip().lower()
    if keyword == "confirm":
        if raw == "confirm" or "confirm" in raw or any(token in raw for token in ["submit", "go ahead", "proceed"]):
            return True
    if keyword == "plan":
        if raw == "plan" or "generate" in raw or "create plan" in raw or "make plan" in raw:
            return True

    llm = gemini_match_choice(
        user_text=value,
        options=["YES", "NO"],
        task_hint=f"Is the user explicitly asking to execute '{keyword}' now? Context: {context}",
    )
    return llm == "YES"


def _normalize_category(value: str) -> str:
    raw = str(value or "").strip().lower()
    mapping = {k.lower(): k for k in FEE_CONFIG.keys()}
    if raw in mapping:
        return mapping[raw]

    # Heuristic matching for natural language.
    if "student" in raw and "foreign" in raw:
        return "Foreign Student"
    if "student" in raw:
        return "Student"
    if "academ" in raw and "foreign" in raw:
        return "Foreign Academician"
    if "academ" in raw:
        return "Academician"
    if "industry" in raw and "foreign" in raw:
        return "Foreign Corporate Delegate"
    if "industry" in raw:
        return "Corporate Delegate"
    if "corporate" in raw:
        return "Corporate Delegate"
    if "delegate" in raw and "foreign" in raw:
        return "Foreign Delegate"

    llm = gemini_match_choice(
        user_text=value,
        options=list(FEE_CONFIG.keys()),
        task_hint="Map user free-text to one conference registration category",
    )
    if llm:
        return llm

    raise AppError("Invalid registration category", ERROR_CODES["VALIDATION_ERROR"], 400)


def _normalize_track(value: str) -> str:
    raw = str(value or "").strip().lower()
    for item in HACKATHON_TRACKS:
        if raw == item.lower():
            return item

    if "health" in raw:
        return "Healthcare"
    if "education" in raw or "school" in raw or "learning" in raw:
        return "Education Transformation"
    if "smart" in raw or "city" in raw or "infra" in raw or "urban" in raw:
        return "Smart City & Infrastructure"

    llm = gemini_match_choice(
        user_text=value,
        options=list(HACKATHON_TRACKS),
        task_hint="Map free-text to one hackathon track",
    )
    if llm:
        return llm

    raise AppError(
        "Invalid track. Choose Healthcare, Education Transformation, or Smart City & Infrastructure.",
        ERROR_CODES["VALIDATION_ERROR"],
        400,
    )


def _normalize_safari_route(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"route 01", "route 1", "1", "01"}:
        return ROUTE_CHOICES["Route 01"]
    if normalized in {"route 02", "route 2", "2", "02"}:
        return ROUTE_CHOICES["Route 02"]
    if normalized in {"route 03", "route 3", "3", "03"}:
        return ROUTE_CHOICES["Route 03"]

    if "spiritual" in normalized or "sacred" in normalized:
        return ROUTE_CHOICES["Route 01"]
    if "urban" in normalized or "heritage" in normalized:
        return ROUTE_CHOICES["Route 02"]
    if "industrial" in normalized or "rural" in normalized:
        return ROUTE_CHOICES["Route 03"]

    llm = gemini_match_choice(
        user_text=value,
        options=list(ROUTE_CHOICES.keys()),
        task_hint="Map free-text to one safari route among Route 01, Route 02, Route 03",
    )
    if llm:
        return ROUTE_CHOICES[llm]

    raise AppError("Choose Route 01, Route 02, or Route 03.", ERROR_CODES["VALIDATION_ERROR"], 400)


def _normalize_planner_pace(value: str) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"slow", "balanced", "packed"}:
        return raw

    if any(token in raw for token in ["relax", "light", "easy", "slow"]):
        return "slow"
    if any(token in raw for token in ["busy", "intense", "full", "packed"]):
        return "packed"
    if any(token in raw for token in ["normal", "balanced", "moderate"]):
        return "balanced"

    llm = gemini_match_choice(
        user_text=value,
        options=["slow", "balanced", "packed"],
        task_hint="Classify preferred event pace",
    )
    if llm:
        return llm

    raise AppError("Pace must be slow, balanced, or packed.", ERROR_CODES["VALIDATION_ERROR"], 400)


def _conference_prompt(step: str, data: Dict) -> str:
    if step == "CONSENT":
        return "Welcome 👋 I can complete your *actual GDTA 2026 conference registration*. Do you consent to proceed? (Yes/No)"
    if step == "NAME":
        return "Great — what is your full name?"
    if step == "INSTITUTION":
        return "Which institution/organization are you from?"
    if step == "ROLE":
        return "What is your designation/role?"
    if step == "CATEGORY":
        return "Choose your registration category: " + ", ".join(FEE_CONFIG.keys())
    if step == "ADDON_FOOD":
        return "Would you like Food & Accommodation add-on? (Yes/No)"
    if step == "ADDON_SAFARI":
        return "Would you like Safari add-on? (Yes/No)"
    if step == "SAFARI_ROUTE":
        return "Choose safari route: Route 01, Route 02, or Route 03"
    if step == "GDTA_MEMBER":
        return "Are you a GDTA member? (Yes/No)"
    if step == "GDTA_AFFILIATION":
        return "Please enter your GDTA affiliation (or type 'NA')."
    if step == "COUNTRY":
        return "Which country are you from?"
    if step == "STATE":
        return "Which state are you from?"
    if step == "EMAIL":
        return "Share your email address for registration confirmation."
    if step == "CONFIRM":
        summary = (
            f"Please confirm ✅\n"
            f"Name: {data.get('name')}\n"
            f"Institution: {data.get('institution')}\n"
            f"Role: {data.get('role')}\n"
            f"Category: {data.get('registration_category')}\n"
            f"Food add-on: {'Yes' if data.get('addon_food') else 'No'}\n"
            f"Safari add-on: {'Yes' if data.get('addon_safari') else 'No'}\n"
            f"Safari route: {data.get('safari_route') or '-'}\n"
            f"GDTA member: {data.get('gdta_member')}\n"
            f"GDTA affiliation: {data.get('gdta_affiliation') or '-'}\n"
            f"Country/State: {data.get('country')} / {data.get('state') or '-'}\n"
            f"Email: {data.get('email')}\n\n"
            f"Type 'confirm' to submit the actual registration."
        )
        return summary
    return "Thanks."


def _hackathon_prompt(step: str, data: Dict) -> str:
    if step == "NAME":
        return "Let’s register you for the hackathon 🚀 What is your full name?"
    if step == "EMAIL":
        return "Your email address?"
    if step == "PHONE":
        return "Your phone number (with country code if possible)?"
    if step == "COLLEGE":
        return "Your college/organization name?"
    if step == "TRACK":
        return "Choose preferred track: Healthcare, Education Transformation, Smart City & Infrastructure"
    if step == "CONFIRM":
        return (
            "Please confirm hackathon registration details:\n"
            f"Name: {data.get('name')}\n"
            f"Email: {data.get('email')}\n"
            f"Phone: {data.get('phone')}\n"
            f"College: {data.get('college')}\n"
            f"Track: {data.get('track')}\n\n"
            "Type 'confirm' to submit."
        )
    return "Thanks."


def _planner_prompt(step: str, data: Dict) -> str:
    if step == "INTERESTS":
        return "Tell me your interests for the 2-day plan (example: workshops, networking, keynote, safari)."
    if step == "PACE":
        return "What pace do you prefer? (slow / balanced / packed)"
    if step == "CONFIRM":
        return (
            "Great. Type 'plan' and I will generate your 2-day event plan based on your interests and pace."
        )
    return "Thanks."


def _assistant_prompt() -> str:
    return "Ask me anything about GDTA 2026."


def _planner_result(data: Dict) -> Dict:
    interests = data.get("interests", "general conference")
    pace = str(data.get("pace", "balanced")).lower()

    day_start = "09:00"
    if pace == "slow":
        day_start = "09:30"
    elif pace == "packed":
        day_start = "08:30"

    return {
        "day_1": [
            {"time": day_start, "activity": "Opening + keynote"},
            {"time": "11:00", "activity": f"Focused sessions on {interests}"},
            {"time": "13:00", "activity": "Networking lunch"},
            {"time": "15:00", "activity": "Hands-on workshop"},
            {"time": "17:00", "activity": "Reflection + expo walk"},
        ],
        "day_2": [
            {"time": day_start, "activity": "Theme recap + community coffee"},
            {"time": "10:30", "activity": f"Advanced sessions for {interests}"},
            {"time": "13:00", "activity": "Mentor connect + lunch"},
            {"time": "15:00", "activity": "Hack/demo showcase"},
            {"time": "17:30", "activity": "Closing + next steps"},
        ],
    }


def _session_payload(mode: str) -> Dict:
    if mode == "conference_registration":
        return {
            "mode": mode,
            "step": "CONSENT",
            "data": {},
            "is_completed": False,
            "created_at": _ts(),
            "updated_at": _ts(),
        }
    if mode == "hackathon_registration":
        return {
            "mode": mode,
            "step": "NAME",
            "data": {},
            "is_completed": False,
            "created_at": _ts(),
            "updated_at": _ts(),
        }
    if mode == "event_planner":
        return {
            "mode": mode,
            "step": "INTERESTS",
            "data": {},
            "is_completed": False,
            "created_at": _ts(),
            "updated_at": _ts(),
        }
    if mode == "conference_assistant":
        return {
            "mode": mode,
            "step": "ASK",
            "data": {},
            "is_completed": False,
            "created_at": _ts(),
            "updated_at": _ts(),
        }
    raise AppError("Unsupported chatbot mode", ERROR_CODES["VALIDATION_ERROR"], 400)


def start_chat_session(mode: str) -> Dict:
    payload = _session_payload(mode)
    session_id = str(uuid.uuid4())
    create_document(CHATBOT_SESSIONS_COLLECTION, payload, doc_id=session_id)

    if mode == "conference_registration":
        bot_message = _conference_prompt("CONSENT", payload["data"])
    elif mode == "hackathon_registration":
        bot_message = _hackathon_prompt("NAME", payload["data"])
    elif mode == "conference_assistant":
        bot_message = _assistant_prompt()
    else:
        bot_message = _planner_prompt("INTERESTS", payload["data"])

    return {
        "session_id": session_id,
        "mode": mode,
        "completed": False,
        "bot_message": bot_message,
    }


def get_chat_session(session_id: str) -> Dict:
    session = get_document(CHATBOT_SESSIONS_COLLECTION, session_id)
    if not session:
        raise AppError("Chat session not found", ERROR_CODES["NOT_FOUND"], 404)
    return session


def reset_chat_session(session_id: str) -> Dict:
    session = get_chat_session(session_id)
    payload = _session_payload(session["mode"])
    update_document(CHATBOT_SESSIONS_COLLECTION, session_id, payload)

    if session["mode"] == "conference_registration":
        bot_message = _conference_prompt("CONSENT", {})
    elif session["mode"] == "hackathon_registration":
        bot_message = _hackathon_prompt("NAME", {})
    elif session["mode"] == "conference_assistant":
        bot_message = _assistant_prompt()
    else:
        bot_message = _planner_prompt("INTERESTS", {})

    return {"session_id": session_id, "mode": session["mode"], "completed": False, "bot_message": bot_message}


def _handle_conference(session: Dict, message: str) -> Tuple[Dict, Dict]:
    step = session.get("step")
    data = dict(session.get("data") or {})
    msg = str(message or "").strip()

    if step == "CONSENT":
        if not _normalize_yes_no(msg, context="conference consent"):
            raise AppError("Please reply Yes to continue registration.", ERROR_CODES["VALIDATION_ERROR"], 400)
        data["consent"] = "Yes"
        next_step = "NAME"

    elif step == "NAME":
        if len(msg) < 2:
            raise AppError("Name must be at least 2 characters.", ERROR_CODES["VALIDATION_ERROR"], 400)
        data["name"] = msg
        next_step = "INSTITUTION"

    elif step == "INSTITUTION":
        if len(msg) < 2:
            raise AppError("Institution is required.", ERROR_CODES["VALIDATION_ERROR"], 400)
        data["institution"] = msg
        next_step = "ROLE"

    elif step == "ROLE":
        if len(msg) < 2:
            raise AppError("Role is required.", ERROR_CODES["VALIDATION_ERROR"], 400)
        data["role"] = msg
        next_step = "CATEGORY"

    elif step == "CATEGORY":
        category = _normalize_category(msg)
        data["registration_category"] = category
        if category in FIXED_FEE_CATEGORIES:
            data["addon_food"] = False
            data["addon_food_accommodation"] = "No"
            data["addon_safari"] = False
            data["safari_route"] = ""
            next_step = "GDTA_MEMBER"
        else:
            next_step = "ADDON_FOOD"

    elif step == "ADDON_FOOD":
        data["addon_food"] = _normalize_yes_no(msg, context="food and accommodation add-on")
        data["addon_food_accommodation"] = "Yes" if data["addon_food"] else "No"
        next_step = "ADDON_SAFARI"

    elif step == "ADDON_SAFARI":
        data["addon_safari"] = _normalize_yes_no(msg, context="safari add-on")
        if data["addon_safari"]:
            next_step = "SAFARI_ROUTE"
        else:
            data["safari_route"] = ""
            next_step = "GDTA_MEMBER"

    elif step == "SAFARI_ROUTE":
        data["safari_route"] = _normalize_safari_route(msg)
        next_step = "GDTA_MEMBER"

    elif step == "GDTA_MEMBER":
        data["gdta_member"] = "Yes" if _normalize_yes_no(msg, context="gdta membership") else "No"
        if data["gdta_member"] == "Yes":
            next_step = "GDTA_AFFILIATION"
        else:
            data["gdta_affiliation"] = ""
            next_step = "COUNTRY"

    elif step == "GDTA_AFFILIATION":
        data["gdta_affiliation"] = "" if msg.lower() in {"na", "none"} else msg
        next_step = "COUNTRY"

    elif step == "COUNTRY":
        if len(msg) < 2:
            raise AppError("Country is required.", ERROR_CODES["VALIDATION_ERROR"], 400)
        data["country"] = msg
        next_step = "STATE" if msg.strip().lower() == "india" else "EMAIL"
        if next_step == "EMAIL":
            data["state"] = ""

    elif step == "STATE":
        if len(msg) < 2:
            raise AppError("State is required for India registrations.", ERROR_CODES["VALIDATION_ERROR"], 400)
        data["state"] = msg
        next_step = "EMAIL"

    elif step == "EMAIL":
        if "@" not in msg or "." not in msg:
            raise AppError("Please enter a valid email.", ERROR_CODES["VALIDATION_ERROR"], 400)
        data["email"] = msg.lower()
        next_step = "CONFIRM"

    elif step == "CONFIRM":
        if not _is_confirm_command(msg, keyword="confirm", context="conference final submission"):
            raise AppError("Type 'confirm' to submit registration.", ERROR_CODES["VALIDATION_ERROR"], 400)

        payload = {
            "consent": "Yes",
            "name": data["name"],
            "title": data.get("title", ""),
            "gender": data.get("gender", ""),
            "institution": data["institution"],
            "role": data["role"],
            "registration_category": data["registration_category"],
            "addon_food": bool(data.get("addon_food", False)),
            "addon_food_accommodation": "Yes" if data.get("addon_food") else "No",
            "addon_safari": bool(data.get("addon_safari", False)),
            "safari_route": data.get("safari_route") or "",
            "gdta_member": data.get("gdta_member") or "No",
            "gdta_affiliation": data.get("gdta_affiliation") or "",
            "country": data.get("country") or "",
            "state": data.get("state") or "",
            "email": data["email"],
            "event_id": CONFERENCE_EVENT_ID,
        }

        registration = submit_registration(payload)
        registration_id = registration["registration_id"]
        payment_data = None
        payment_error = None

        try:
            payment_data = create_payment_link(
                actor_uid="chatbot",
                registration_id=registration_id,
                name=data["name"],
                email=data["email"],
                category=data["registration_category"],
                addon_food=bool(data.get("addon_food", False)),
                addon_safari=bool(data.get("addon_safari", False)),
                idempotency_key=f"chatbot-{session['id']}",
                payment_method="UPI",
            )
        except AppError as exc:
            payment_error = exc.message

        next_step = "COMPLETED"
        response = {
            "session_id": session["id"],
            "mode": "conference_registration",
            "completed": True,
            "bot_message": "✅ Conference registration submitted successfully!",
            "registration": registration,
            "payment": payment_data,
            "payment_error": payment_error,
        }
        return ({"step": next_step, "data": data, "is_completed": True}, response)

    else:
        raise AppError("This chat session is already completed.", ERROR_CODES["INVALID_STATE"], 400)

    response = {
        "session_id": session["id"],
        "mode": "conference_registration",
        "completed": False,
        "bot_message": _conference_prompt(next_step, data),
        "step": next_step,
    }
    return ({"step": next_step, "data": data, "is_completed": False}, response)


def _handle_hackathon(session: Dict, message: str) -> Tuple[Dict, Dict]:
    step = session.get("step")
    data = dict(session.get("data") or {})
    msg = str(message or "").strip()

    if step == "NAME":
        if len(msg) < 2:
            raise AppError("Name must be at least 2 characters.", ERROR_CODES["VALIDATION_ERROR"], 400)
        data["name"] = msg
        next_step = "EMAIL"

    elif step == "EMAIL":
        if "@" not in msg or "." not in msg:
            raise AppError("Please enter a valid email.", ERROR_CODES["VALIDATION_ERROR"], 400)
        data["email"] = msg.lower()
        next_step = "PHONE"

    elif step == "PHONE":
        if len(msg) < 8:
            raise AppError("Phone number looks too short.", ERROR_CODES["VALIDATION_ERROR"], 400)
        data["phone"] = msg
        next_step = "COLLEGE"

    elif step == "COLLEGE":
        if len(msg) < 2:
            raise AppError("College/organization is required.", ERROR_CODES["VALIDATION_ERROR"], 400)
        data["college"] = msg
        next_step = "TRACK"

    elif step == "TRACK":
        data["track"] = _normalize_track(msg)
        next_step = "CONFIRM"

    elif step == "CONFIRM":
        if not _is_confirm_command(msg, keyword="confirm", context="hackathon final submission"):
            raise AppError("Type 'confirm' to submit hackathon registration.", ERROR_CODES["VALIDATION_ERROR"], 400)

        existing = query_documents(HACKATHON_COLLECTION, filters=[("email", "==", data["email"])], limit=1)
        if existing:
            raise AppError("This email is already registered for hackathon.", ERROR_CODES["DUPLICATE_EMAIL"], 409)

        doc = {
            "name": data["name"],
            "email": data["email"],
            "phone": data["phone"],
            "college": data["college"],
            "track": data["track"],
            "status": "new",
            "admin_notes": "",
            "ticket_history": [{"at": _ts(), "status": "new", "notes": "registered via chatbot"}],
            "created_at": _ts(),
            "updated_at": _ts(),
        }
        registration_id = create_document(HACKATHON_COLLECTION, doc)

        response = {
            "session_id": session["id"],
            "mode": "hackathon_registration",
            "completed": True,
            "bot_message": "✅ Hackathon registration submitted successfully!",
            "registration": {"registration_id": registration_id, **doc},
        }
        return ({"step": "COMPLETED", "data": data, "is_completed": True}, response)

    else:
        raise AppError("This chat session is already completed.", ERROR_CODES["INVALID_STATE"], 400)

    response = {
        "session_id": session["id"],
        "mode": "hackathon_registration",
        "completed": False,
        "bot_message": _hackathon_prompt(next_step, data),
        "step": next_step,
    }
    return ({"step": next_step, "data": data, "is_completed": False}, response)


def _handle_planner(session: Dict, message: str) -> Tuple[Dict, Dict]:
    step = session.get("step")
    data = dict(session.get("data") or {})
    msg = str(message or "").strip()

    if step == "INTERESTS":
        if len(msg) < 2:
            raise AppError("Please share at least one interest.", ERROR_CODES["VALIDATION_ERROR"], 400)
        data["interests"] = msg
        next_step = "PACE"

    elif step == "PACE":
        data["pace"] = _normalize_planner_pace(msg)
        next_step = "CONFIRM"

    elif step == "CONFIRM":
        if not _is_confirm_command(msg, keyword="plan", context="planner generation"):
            raise AppError("Type 'plan' to generate your itinerary.", ERROR_CODES["VALIDATION_ERROR"], 400)
        plan = _planner_result(data)
        response = {
            "session_id": session["id"],
            "mode": "event_planner",
            "completed": True,
            "bot_message": "🗓️ Your personalized 2-day event plan is ready.",
            "plan": plan,
        }
        return ({"step": "COMPLETED", "data": data, "is_completed": True}, response)

    else:
        raise AppError("This chat session is already completed.", ERROR_CODES["INVALID_STATE"], 400)

    response = {
        "session_id": session["id"],
        "mode": "event_planner",
        "completed": False,
        "bot_message": _planner_prompt(next_step, data),
        "step": next_step,
    }
    return ({"step": next_step, "data": data, "is_completed": False}, response)


def _handle_conference_assistant(session: Dict, message: str) -> Tuple[Dict, Dict]:
    data = dict(session.get("data") or {})
    msg = str(message or "").strip()
    if not msg:
        raise AppError("Please enter your question.", ERROR_CODES["VALIDATION_ERROR"], 400)

    if msg.lower() in {"help", "menu", "options"}:
        return (
            {"step": "ASK", "data": data, "is_completed": False},
            {
                "session_id": session["id"],
                "mode": "conference_assistant",
                "completed": False,
                "bot_message": _assistant_prompt(),
                "step": "ASK",
                "rag_sources": [],
            },
        )

    rag = rag_answer_query(msg)
    source_lines = ""
    if rag.get("sources"):
        source_lines = "\n\nSources:\n" + "\n".join([f"- {s}" for s in rag["sources"]])

    return (
        {"step": "ASK", "data": data, "is_completed": False},
        {
            "session_id": session["id"],
            "mode": "conference_assistant",
            "completed": False,
            "bot_message": f"{rag.get('answer', 'No answer found.')}{source_lines}",
            "step": "ASK",
            "rag_sources": rag.get("sources") or [],
        },
    )


def process_chat_message(*, session_id: str, message: str) -> Dict:
    session = get_chat_session(session_id)
    if session.get("is_completed"):
        raise AppError("Session already completed. Start a new one.", ERROR_CODES["INVALID_STATE"], 400)

    mode = session.get("mode")
    if mode == "conference_registration":
        patch, response = _handle_conference(session, message)
    elif mode == "hackathon_registration":
        patch, response = _handle_hackathon(session, message)
    elif mode == "event_planner":
        patch, response = _handle_planner(session, message)
    elif mode == "conference_assistant":
        patch, response = _handle_conference_assistant(session, message)
    else:
        raise AppError("Unsupported chatbot mode", ERROR_CODES["VALIDATION_ERROR"], 400)

    update_document(
        CHATBOT_SESSIONS_COLLECTION,
        session_id,
        {
            "step": patch["step"],
            "data": patch["data"],
            "is_completed": patch["is_completed"],
            "updated_at": _ts(),
        },
    )
    return response
