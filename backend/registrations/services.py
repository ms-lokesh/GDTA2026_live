import uuid
from datetime import datetime

from core.constants import COLLECTIONS, ERROR_CODES
from core.exceptions import AppError
from services.firebase.firestore import create_document, get_document, query_documents, update_document

from .state_machine import compute_fee, initial_state, process


def _yes(value):
    return str(value or "").strip().lower() in {"yes", "y", "true", "1"}


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

    if str(payload.get("consent") or "").strip().lower() not in {"yes", "y", "true", "1"}:
        raise AppError("Registration requires consent", ERROR_CODES["VALIDATION_ERROR"], 400)

    gdta_member_raw = str(payload.get("gdta_member") or "").strip()
    if not gdta_member_raw:
        raise AppError("GDTA member response is required", ERROR_CODES["VALIDATION_ERROR"], 400)

    gdta_member = gdta_member_raw.lower()
    if gdta_member not in {"yes", "y", "true", "1", "no", "n", "false", "0"}:
        raise AppError("GDTA member must be Yes or No", ERROR_CODES["VALIDATION_ERROR"], 400)

    if _yes(gdta_member_raw) and not str(payload.get("gdta_affiliation") or "").strip():
        raise AppError("GDTA affiliation is required when GDTA member is Yes", ERROR_CODES["VALIDATION_ERROR"], 400)

    duplicate = query_documents(COLLECTIONS["registrations"], filters=[("email", "==", email)], limit=1)
    if duplicate:
        existing = duplicate[0]
        if str(existing.get("payment_status") or "").lower() == "paid":
            raise AppError("Email already registered and payment is already completed", ERROR_CODES["DUPLICATE_EMAIL"], 409)
        return {
            "registration_id": existing.get("id"),
            "unique_id": existing.get("unique_id"),
            "reused_registration": True,
        }

    addon_food = _yes(payload.get("addon_food")) or _yes(payload.get("addon_food_accommodation"))
    addon_safari = _yes(payload.get("addon_safari"))

    if addon_safari and not str(payload.get("safari_route") or "").strip():
        raise AppError("Safari route required when safari add-on is selected", ERROR_CODES["VALIDATION_ERROR"], 400)

    country = str(payload.get("country") or "").strip()
    if country.lower() == "india" and not str(payload.get("state") or "").strip():
        raise AppError("State required for registrations from India", ERROR_CODES["VALIDATION_ERROR"], 400)

    fee = compute_fee(
        payload.get("registration_category"),
        addon_food=addon_food,
        addon_safari=addon_safari,
    )
    if not fee:
        raise AppError("Invalid category", ERROR_CODES["VALIDATION_ERROR"], 400)

    doc = {
        **payload,
        **fee,
        "addon_food_accommodation": "Yes" if addon_food else "No",
        "addon_safari": "Yes" if addon_safari else "No",
        "email": email,
        "status": "pending",
        "payment_status": "payment_pending",
        "payment_link": None,
        "invoice_id": None,
        "payment_amount": fee["total_fee"],
        "currency": fee["fee_currency"],
        "unique_id": str(uuid.uuid4()).replace("-", "")[:10].upper(),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    doc_id = create_document(COLLECTIONS["registrations"], doc)
    return {"registration_id": doc_id, "unique_id": doc["unique_id"]}
