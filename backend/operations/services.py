from datetime import datetime

from core.audit import write_audit_log
from core.constants import COLLECTIONS, ERROR_CODES
from core.exceptions import AppError
from services.firebase.firestore import create_document, delete_document, get_document, query_documents, update_document
from utils.permissions import assert_event_scope


def list_venues(user):
    all_rows = query_documents(COLLECTIONS["venues"])
    allowed = set(user.get("event_ids", []))
    if not allowed:
        return all_rows
    return [v for v in all_rows if v.get("event_id") in allowed]


def create_venue(payload, actor_user):
    assert_event_scope(actor_user, payload.get("event_id"))
    payload = {
        **payload,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    venue_id = create_document(COLLECTIONS["venues"], payload)
    write_audit_log("venue_created", actor_user.get("uid"), target={"venue_id": venue_id}, details={"event_id": payload.get("event_id")})
    return venue_id


def update_venue(venue_id, payload, actor_user):
    existing = get_document(COLLECTIONS["venues"], venue_id)
    if not existing:
        raise AppError("Venue not found", ERROR_CODES["NOT_FOUND"], 404)
    assert_event_scope(actor_user, existing.get("event_id"))
    payload = {**payload, "updated_at": datetime.utcnow().isoformat()}
    update_document(COLLECTIONS["venues"], venue_id, payload)
    write_audit_log("venue_updated", actor_user.get("uid"), target={"venue_id": venue_id}, details={"patch": payload})
    return True


def delete_venue(venue_id, actor_user):
    existing = get_document(COLLECTIONS["venues"], venue_id)
    if not existing:
        raise AppError("Venue not found", ERROR_CODES["NOT_FOUND"], 404)
    assert_event_scope(actor_user, existing.get("event_id"))
    delete_document(COLLECTIONS["venues"], venue_id)
    write_audit_log("venue_deleted", actor_user.get("uid"), target={"venue_id": venue_id}, details={"event_id": existing.get("event_id")})
    return True


def validate_qr(unique_id, venue_id, scanned_by):
    regs = query_documents(COLLECTIONS["registrations"], filters=[("unique_id", "==", unique_id)], limit=1)
    reg = regs[0] if regs else None
    if not reg:
        raise AppError("Invalid QR code", ERROR_CODES["NOT_FOUND"], 404)

    if reg.get("status") != "approved":
        raise AppError("Registration not approved", ERROR_CODES["FORBIDDEN"], 403)

    venue = get_document(COLLECTIONS["venues"], venue_id)
    if not venue:
        raise AppError("Venue not found", ERROR_CODES["NOT_FOUND"], 404)

    if not venue.get("is_active", True):
        raise AppError("Venue is inactive", ERROR_CODES["FORBIDDEN"], 403)

    access_limit = str(venue.get("access_limit", "unlimited"))
    prior = query_documents(
        COLLECTIONS["access_logs"],
        filters=[
            ("registration_id", "==", reg.get("id")),
            ("venue_id", "==", venue_id),
            ("action_type", "==", "check-in"),
        ],
    )
    count = len(prior)
    if access_limit == "once" and count > 0:
        raise AppError("Access limit reached", ERROR_CODES["FORBIDDEN"], 403)
    if access_limit.isdigit() and count >= int(access_limit):
        raise AppError("Access limit reached", ERROR_CODES["FORBIDDEN"], 403)

    log_id = create_document(
        COLLECTIONS["access_logs"],
        {
            "registration_id": reg.get("id"),
            "registration_email": reg.get("email"),
            "participant_name": reg.get("name"),
            "event_id": reg.get("event_id"),
            "venue_id": venue_id,
            "venue_name": venue.get("name"),
            "action_type": "check-in",
            "scanned_by": scanned_by,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )
    write_audit_log(
        "qr_validated",
        scanned_by,
        target={"registration_id": reg.get("id"), "venue_id": venue_id},
        details={"access_limit": access_limit, "prior_count": count},
    )

    return {"access_granted": True, "access_log_id": log_id, "registration": reg, "venue": venue}
