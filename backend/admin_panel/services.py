import csv
import io
import os
from collections import Counter
from datetime import datetime

import qrcode
from PIL import Image, ImageDraw, ImageFont

from core.audit import write_audit_log
from core.constants import COLLECTIONS, ERROR_CODES
from core.exceptions import AppError
from services.firebase.firestore import create_document, get_collection, get_document, query_documents, update_document
from utils.permissions import assert_event_scope


def _scope_rows(user, rows):
    if user.get("role") == "SUPER_ADMIN":
        return rows
    allowed = set(user.get("event_ids", []))
    return [r for r in rows if r.get("event_id") in allowed]


def list_registrations(user, filters):
    rows = query_documents(COLLECTIONS["registrations"])
    rows = _scope_rows(user, rows)

    status_filter = filters.get("status")
    event_filter = filters.get("event_id")
    search = (filters.get("search") or "").lower().strip()

    if status_filter:
        rows = [r for r in rows if r.get("status") == status_filter]
    if event_filter:
        rows = [r for r in rows if r.get("event_id") == event_filter]
    if search:
        rows = [
            r
            for r in rows
            if search in (r.get("name") or "").lower()
            or search in (r.get("email") or "").lower()
            or search in (r.get("institution") or "").lower()
        ]

    return rows


def bulk_update_status(actor_user, registration_ids, status):
    updated = 0
    for reg_id in registration_ids:
        registration = get_document(COLLECTIONS["registrations"], reg_id)
        if not registration:
            continue
        assert_event_scope(actor_user, registration.get("event_id"))
        update_document(COLLECTIONS["registrations"], reg_id, {"status": status, "status_updated_at": datetime.utcnow().isoformat()})
        write_audit_log(
            "registration_status_updated",
            actor_user.get("uid"),
            target={"registration_id": reg_id},
            details={"new_status": status},
        )
        updated += 1
    return updated


def get_stats(user):
    rows = _scope_rows(user, query_documents(COLLECTIONS["registrations"]))

    status_counts = Counter([r.get("status", "pending") for r in rows])
    country_counts = Counter([r.get("country", "Unknown") for r in rows])
    payment_counts = Counter([r.get("payment_status", "payment_pending") for r in rows])

    return {
        "total_registrations": len(rows),
        "status_breakdown": dict(status_counts),
        "country_distribution": dict(country_counts),
        "payment_status_breakdown": dict(payment_counts),
    }


def _rows_to_csv(rows, ordered_fields):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=ordered_fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def export_registrations(user, filters):
    rows = list_registrations(user, filters)
    ordered = [
        "id",
        "event_id",
        "name",
        "email",
        "institution",
        "status",
        "country",
        "registration_category",
        "payment_status",
        "payment_amount",
        "currency",
        "created_at",
    ]
    return _rows_to_csv(rows, ordered)


def export_venues(user, filters):
    rows = _scope_rows(user, query_documents(COLLECTIONS["venues"]))
    event_filter = filters.get("event_id")
    if event_filter:
        rows = [r for r in rows if r.get("event_id") == event_filter]
    ordered = ["id", "event_id", "name", "venue_type", "location", "capacity", "is_active", "access_limit", "created_at"]
    return _rows_to_csv(rows, ordered)


def export_access_logs(user, filters):
    rows = _scope_rows(user, query_documents(COLLECTIONS["access_logs"]))
    event_filter = filters.get("event_id")
    if event_filter:
        rows = [r for r in rows if r.get("event_id") == event_filter]
    ordered = [
        "id",
        "event_id",
        "registration_id",
        "registration_email",
        "participant_name",
        "venue_id",
        "venue_name",
        "action_type",
        "scanned_by",
        "timestamp",
    ]
    return _rows_to_csv(rows, ordered)


def _user_rows_by_role(role, actor_user):
    rows = query_documents(COLLECTIONS["users"])
    rows = [r for r in rows if r.get("role") == role]
    if actor_user.get("role") == "SUPER_ADMIN":
        return rows
    allowed = set(actor_user.get("event_ids", []))
    return [r for r in rows if bool(allowed.intersection(set(r.get("event_ids", []))))]


def list_users_by_role(role, actor_user):
    return _user_rows_by_role(role, actor_user)


def create_user_with_role(role, payload, actor_user):
    if actor_user.get("role") != "SUPER_ADMIN":
        raise AppError("Only super admin can create admins/volunteers", ERROR_CODES["FORBIDDEN"], 403)
    now = datetime.utcnow().isoformat()
    doc = {
        **payload,
        "role": role,
        "created_at": now,
        "updated_at": now,
        "created_by": actor_user.get("uid"),
    }
    create_document(COLLECTIONS["users"], doc, doc_id=payload["uid"])
    write_audit_log("user_role_created", actor_user.get("uid"), target={"uid": payload["uid"]}, details={"role": role})
    return get_document(COLLECTIONS["users"], payload["uid"])


def update_user_with_role(role, user_id, patch, actor_user):
    existing = get_document(COLLECTIONS["users"], user_id)
    if not existing or existing.get("role") != role:
        raise AppError("User not found", ERROR_CODES["NOT_FOUND"], 404)
    if actor_user.get("role") != "SUPER_ADMIN":
        raise AppError("Only super admin can update admins/volunteers", ERROR_CODES["FORBIDDEN"], 403)
    update_document(COLLECTIONS["users"], user_id, {**patch, "updated_at": datetime.utcnow().isoformat()})
    write_audit_log("user_role_updated", actor_user.get("uid"), target={"uid": user_id}, details={"role": role, "patch": patch})
    return get_document(COLLECTIONS["users"], user_id)


def delete_user_with_role(role, user_id, actor_user):
    existing = get_document(COLLECTIONS["users"], user_id)
    if not existing or existing.get("role") != role:
        raise AppError("User not found", ERROR_CODES["NOT_FOUND"], 404)
    if actor_user.get("role") != "SUPER_ADMIN":
        raise AppError("Only super admin can delete admins/volunteers", ERROR_CODES["FORBIDDEN"], 403)
    update_document(COLLECTIONS["users"], user_id, {"is_active": False, "deleted_at": datetime.utcnow().isoformat()})
    write_audit_log("user_role_deleted", actor_user.get("uid"), target={"uid": user_id}, details={"role": role})
    return True


def _generated_ids_dir():
    target = os.path.join(os.path.dirname(os.path.dirname(__file__)), "generated_ids")
    os.makedirs(target, exist_ok=True)
    return target


def _build_id_card_image(registration):
    width, height = 900, 560
    image = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    font_title = ImageFont.load_default()
    font_text = ImageFont.load_default()

    draw.rectangle([(20, 20), (880, 540)], outline=(30, 30, 30), width=3)
    draw.text((40, 40), "GDTA 2026 - Participant ID Card", fill=(0, 0, 0), font=font_title)
    draw.text((40, 110), f"Name: {registration.get('name', '')}", fill=(0, 0, 0), font=font_text)
    draw.text((40, 150), f"Email: {registration.get('email', '')}", fill=(0, 0, 0), font=font_text)
    draw.text((40, 190), f"Category: {registration.get('registration_category', '')}", fill=(0, 0, 0), font=font_text)
    draw.text((40, 230), f"Unique ID: {registration.get('unique_id', '')}", fill=(0, 0, 0), font=font_text)

    qr = qrcode.make(registration.get("unique_id") or registration.get("id"))
    qr = qr.resize((220, 220))
    image.paste(qr, (620, 180))

    return image


def generate_id_card(registration_id, actor_user, force_regenerate=False):
    registration = get_document(COLLECTIONS["registrations"], registration_id)
    if not registration:
        raise AppError("Registration not found", ERROR_CODES["NOT_FOUND"], 404)

    assert_event_scope(actor_user, registration.get("event_id"))

    existing = query_documents(COLLECTIONS["id_cards"], filters=[("registration_id", "==", registration_id)], limit=1)
    existing_card = existing[0] if existing else None
    if existing_card and not force_regenerate:
        return existing_card

    image = _build_id_card_image(registration)
    file_name = f"id_card_{registration_id}_{int(datetime.utcnow().timestamp())}.png"
    file_path = os.path.join(_generated_ids_dir(), file_name)
    image.save(file_path, format="PNG")

    payload = {
        "registration_id": registration_id,
        "event_id": registration.get("event_id"),
        "unique_id": registration.get("unique_id"),
        "file_path": file_path,
        "status": "generated",
        "generated_by": actor_user.get("uid"),
        "generated_at": datetime.utcnow().isoformat(),
    }

    if existing_card:
        update_document(COLLECTIONS["id_cards"], existing_card["id"], payload)
        card = get_document(COLLECTIONS["id_cards"], existing_card["id"])
    else:
        card_id = create_document(COLLECTIONS["id_cards"], payload)
        card = get_document(COLLECTIONS["id_cards"], card_id)

    write_audit_log(
        "id_card_generated",
        actor_user.get("uid"),
        target={"registration_id": registration_id},
        details={"force_regenerate": force_regenerate, "file_path": file_path},
    )
    return card


def get_id_card_status(registration_id, actor_user):
    registration = get_document(COLLECTIONS["registrations"], registration_id)
    if not registration:
        raise AppError("Registration not found", ERROR_CODES["NOT_FOUND"], 404)
    assert_event_scope(actor_user, registration.get("event_id"))

    rows = query_documents(COLLECTIONS["id_cards"], filters=[("registration_id", "==", registration_id)], limit=1)
    if not rows:
        return {"registration_id": registration_id, "status": "not_generated", "file_path": None}
    return rows[0]


def delete_firestore_document(collection, doc_id):
    get_collection(collection).document(doc_id).delete()
    return True
