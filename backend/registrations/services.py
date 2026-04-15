import uuid
from datetime import datetime

from core.constants import COLLECTIONS, ERROR_CODES
from core.exceptions import AppError
from services.firebase.firestore import create_document, get_document, query_documents, update_document

from .state_machine import compute_fee, initial_state, process


def start_registration(session_id=None):
    sid = session_id or str(uuid.uuid4())
    state = initial_state()
    payload = {"session_id": sid, **state, "updated_at": datetime.utcnow().isoformat()}
    create_document(COLLECTIONS["registration_sessions"], payload, doc_id=sid)
    return payload


def get_session(session_id):
    session = get_document(COLLECTIONS["registration_sessions"], session_id)
    if not session:
        raise AppError("Registration session not found", ERROR_CODES["NOT_FOUND"], 404)
    return session


def answer_registration(session_id, answer):
    session = get_session(session_id)
    if not session.get("is_active", False):
        raise AppError("Registration session inactive", ERROR_CODES["INVALID_STATE"], 400)

    state = {
        "current_step": session.get("current_step"),
        "is_active": session.get("is_active"),
        "data": session.get("data", {}),
    }

    try:
        next_state, message, completed = process(state, answer)
    except ValueError as exc:
        raise AppError(str(exc), ERROR_CODES["VALIDATION_ERROR"], 400) from exc

    update_document(
        COLLECTIONS["registration_sessions"],
        session_id,
        {
            "current_step": next_state["current_step"],
            "is_active": next_state["is_active"],
            "data": next_state["data"],
            "updated_at": datetime.utcnow().isoformat(),
        },
    )

    if completed and next_state["data"].get("email"):
        submit_registration(next_state["data"])

    return {
        "session_id": session_id,
        "current_step": next_state["current_step"],
        "completed": completed,
        "message": message,
        "data": next_state["data"],
    }


def cancel_registration(session_id):
    get_session(session_id)
    update_document(
        COLLECTIONS["registration_sessions"],
        session_id,
        {
            "is_active": False,
            "current_step": "COMPLETE",
            "updated_at": datetime.utcnow().isoformat(),
        },
    )
    return True


def submit_registration(payload):
    email = (payload.get("email") or "").lower().strip()
    if not email:
        raise AppError("Email required", ERROR_CODES["VALIDATION_ERROR"], 400)

    duplicate = query_documents(COLLECTIONS["registrations"], filters=[("email", "==", email)], limit=1)
    if duplicate:
        raise AppError("Email already registered", ERROR_CODES["DUPLICATE_EMAIL"], 409)

    fee = compute_fee(
        payload.get("registration_category"),
        bool(payload.get("addon_food")),
        bool(payload.get("addon_safari")),
    )
    if not fee:
        raise AppError("Invalid category", ERROR_CODES["VALIDATION_ERROR"], 400)

    doc = {
        **payload,
        **fee,
        "email": email,
        "status": "pending",
        "unique_id": str(uuid.uuid4()).replace("-", "")[:10].upper(),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    doc_id = create_document(COLLECTIONS["registrations"], doc)
    return {"registration_id": doc_id, "unique_id": doc["unique_id"]}
