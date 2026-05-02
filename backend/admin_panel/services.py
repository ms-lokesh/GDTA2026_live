import csv
import io
import os
from collections import Counter
from datetime import datetime

import qrcode
from PIL import Image, ImageDraw, ImageFont
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from accounts.signals import invalidate_other_user_sessions
from core.audit import write_audit_log
from core.constants import COLLECTIONS, ERROR_CODES
from core.exceptions import AppError
from services.firebase.firestore import create_document, delete_document, get_document, query_documents, update_document
from utils.permissions import assert_event_scope
from accounts.models import UserProfile
from registrations.models import ConsentRecord


def _scope_rows(user, rows):
    allowed = set(user.get("event_ids", []))
    if not allowed:
        return rows
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


def export_consent_records(user, registration_id):
    registration = get_document(COLLECTIONS["registrations"], registration_id)
    if not registration:
        raise AppError("Registration not found", ERROR_CODES["NOT_FOUND"], 404)
    assert_event_scope(user, registration.get("event_id"))
    records = ConsentRecord.objects.filter(registration__collection=COLLECTIONS["registrations"], registration__doc_id=registration_id)
    rows = [
        {
            "registration_id": registration_id,
            "consent_given": record.consent_given,
            "consent_timestamp": record.consent_timestamp.isoformat(),
            "consent_version": record.consent_version,
            "ip_address": record.ip_address,
            "consent_text": record.consent_text,
        }
        for record in records
    ]
    return _rows_to_csv(rows, ["registration_id", "consent_given", "consent_timestamp", "consent_version", "ip_address", "consent_text"])


def _user_rows_by_role(role, actor_user):
    rows = [profile.as_payload() for profile in UserProfile.objects.select_related("user").filter(role=role)]
    allowed = set(actor_user.get("event_ids", []))
    if not allowed:
        return rows
    return [r for r in rows if bool(allowed.intersection(set(r.get("event_ids", []))))]


def list_users_by_role(role, actor_user):
    return _user_rows_by_role(role, actor_user)


def create_user_with_role(role, payload, actor_user):
    if actor_user.get("role") != "ADMIN":
        raise AppError("Only admins can create admins/volunteers", ERROR_CODES["FORBIDDEN"], 403)
    User = get_user_model()
    username = payload["uid"]
    if User.objects.filter(username=username).exists():
        raise AppError("User already exists", ERROR_CODES["CONFLICT"], 409)

    user = User.objects.create(
        username=username,
        email=payload.get("email", ""),
        is_active=payload.get("is_active", True),
    )
    password = payload.get("password")
    if password:
        validate_password(password, user=user)
        user.set_password(password)
    else:
        user.set_unusable_password()
    user.save()

    profile = UserProfile.objects.create(
        user=user,
        role=role,
        name=payload.get("name", ""),
        phone=payload.get("phone", ""),
        event_ids=payload.get("event_ids", []),
        assigned_venues=payload.get("assigned_venues", []),
        is_active=payload.get("is_active", True),
    )
    write_audit_log("user_role_created", actor_user.get("uid"), target={"uid": username}, details={"role": role})
    return profile.as_payload()


def update_user_with_role(role, user_id, patch, actor_user):
    try:
        profile = UserProfile.objects.select_related("user").get(user__username=user_id, role=role)
    except UserProfile.DoesNotExist:
        raise AppError("User not found", ERROR_CODES["NOT_FOUND"], 404)
    if actor_user.get("role") != "ADMIN":
        raise AppError("Only admins can update admins/volunteers", ERROR_CODES["FORBIDDEN"], 403)
    user = profile.user

    if "email" in patch:
        user.email = patch.get("email") or ""
    if "is_active" in patch:
        user.is_active = bool(patch.get("is_active"))
    if "password" in patch and patch.get("password"):
        validate_password(patch["password"], user=user)
        user.set_password(patch["password"])
        invalidate_other_user_sessions(user)
    user.save()

    if "name" in patch:
        profile.name = patch.get("name") or ""
    if "phone" in patch:
        profile.phone = patch.get("phone") or ""
    if "event_ids" in patch:
        profile.event_ids = patch.get("event_ids") or []
    if "assigned_venues" in patch:
        profile.assigned_venues = patch.get("assigned_venues") or []
    if "is_active" in patch:
        profile.is_active = bool(patch.get("is_active"))
    profile.save()

    safe_patch = {k: v for k, v in patch.items() if k != "password"}
    write_audit_log("user_role_updated", actor_user.get("uid"), target={"uid": user_id}, details={"role": role, "patch": safe_patch})
    return profile.as_payload()


def delete_user_with_role(role, user_id, actor_user):
    try:
        profile = UserProfile.objects.select_related("user").get(user__username=user_id, role=role)
    except UserProfile.DoesNotExist:
        raise AppError("User not found", ERROR_CODES["NOT_FOUND"], 404)
    if actor_user.get("role") != "ADMIN":
        raise AppError("Only admins can delete admins/volunteers", ERROR_CODES["FORBIDDEN"], 403)
    user = profile.user
    user.is_active = False
    user.save(update_fields=["is_active"])
    profile.is_active = False
    profile.save(update_fields=["is_active"])
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
    return delete_document(collection, doc_id)
