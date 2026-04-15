from collections import Counter

from core.constants import COLLECTIONS
from services.firebase.firestore import query_documents, update_document


def list_registrations(user, filters):
    rows = query_documents(COLLECTIONS["registrations"])
    if user.get("role") != "SUPER_ADMIN":
        allowed = set(user.get("event_ids", []))
        rows = [r for r in rows if r.get("event_id") in allowed]

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


def bulk_update_status(registration_ids, status):
    updated = 0
    for reg_id in registration_ids:
        if update_document(COLLECTIONS["registrations"], reg_id, {"status": status}):
            updated += 1
    return updated


def get_stats(user):
    rows = query_documents(COLLECTIONS["registrations"])
    if user.get("role") != "SUPER_ADMIN":
        allowed = set(user.get("event_ids", []))
        rows = [r for r in rows if r.get("event_id") in allowed]

    status_counts = Counter([r.get("status", "pending") for r in rows])
    country_counts = Counter([r.get("country", "Unknown") for r in rows])

    return {
        "total": len(rows),
        "by_status": dict(status_counts),
        "by_country": dict(country_counts),
    }
