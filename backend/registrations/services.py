import uuid
from datetime import datetime
from email.mime.text import MIMEText
import smtplib

from django.conf import settings
from django.core import signing

from core.constants import COLLECTIONS, ERROR_CODES
from core.exceptions import AppError
from datastore.models import Document
from registrations.models import ConsentRecord
from registrations.security import PAYMENT_STATUS_TOKEN_SALT, is_sanctioned_country
from services.firebase.firestore import create_document, get_document, query_documents, update_document

from .state_machine import compute_fee, initial_state, process


def _yes(value):
    return str(value or "").strip().lower() in {"yes", "y", "true", "1"}


def create_payment_status_token(registration_id, email):
    return signing.dumps(
        {"registration_id": registration_id, "email": (email or "").lower().strip()},
        salt=PAYMENT_STATUS_TOKEN_SALT,
    )


def _send_private_email(to_email, subject, message):
    if not getattr(settings, "EMAIL_USERNAME", "") or not getattr(settings, "EMAIL_PASSWORD", ""):
        return False
    msg = MIMEText(message, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_USERNAME}>"
    msg["To"] = to_email
    smtp = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=20)
    try:
        if settings.EMAIL_USE_TLS:
            smtp.starttls()
        smtp.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
        smtp.sendmail(settings.EMAIL_USERNAME, [to_email], msg.as_string())
    finally:
        smtp.quit()
    return True


def send_payment_status_token_email(registration_id, email):
    token = create_payment_status_token(registration_id, email)
    base_url = getattr(settings, "SITE_URL", "https://gdta2026.com").rstrip("/")
    message = (
        "Your GDTA 2026 registration payment-status access link is below. "
        "This link expires in 24 hours.\n\n"
        f"{base_url}/api/payment/status/<ORDER_ID>?token={token}\n\n"
        "Replace <ORDER_ID> with the order ID shown after payment initiation."
    )
    try:
        _send_private_email(email, "Your GDTA 2026 payment status access link", message)
    except Exception:
        pass


def send_existing_registration_notice(email):
    message = (
        "We received a GDTA 2026 registration attempt using this email address. "
        "If this was you, please continue from your existing registration/payment email. "
        "If this was not you, no action is required."
    )
    try:
        _send_private_email(email, "GDTA 2026 registration notice", message)
    except Exception:
        pass


def _client_ip(request_meta=None):
    request_meta = request_meta or {}
    return request_meta.get("REMOTE_ADDR")


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


def submit_registration(payload, request_meta=None):
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

    country = str(payload.get("country") or "").strip()
    if is_sanctioned_country(country):
        raise AppError("Registration not available in your region", ERROR_CODES["VALIDATION_ERROR"], 400)

    duplicate = query_documents(COLLECTIONS["registrations"], filters=[("email", "==", email)], limit=1)
    if duplicate:
        send_existing_registration_notice(email)
        return {"message": "Registration request received"}

    addon_food = _yes(payload.get("addon_food")) or _yes(payload.get("addon_food_accommodation"))
    addon_safari = _yes(payload.get("addon_safari"))

    if addon_safari and not str(payload.get("safari_route") or "").strip():
        raise AppError("Safari route required when safari add-on is selected", ERROR_CODES["VALIDATION_ERROR"], 400)

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
        "unique_id": str(uuid.uuid4()),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    doc_id = create_document(COLLECTIONS["registrations"], doc)
    try:
        registration_document = Document.objects.get(collection=COLLECTIONS["registrations"], doc_id=doc_id)
        ConsentRecord.objects.create(
            registration=registration_document,
            consent_given=True,
            consent_version=getattr(settings, "CONSENT_VERSION", "2026-05-02"),
            ip_address=_client_ip(request_meta),
            consent_text=getattr(settings, "CONSENT_TEXT", ""),
        )
    except Exception:
        pass
    send_payment_status_token_email(doc_id, email)
    return {"registration_id": doc_id, "unique_id": doc["unique_id"]}
