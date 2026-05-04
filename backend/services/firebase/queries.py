from datetime import datetime
from typing import Any, Dict, List, Optional

from core.constants import COLLECTIONS
from services.firebase.firestore import (
    create_document,
    get_document,
    query_documents,
    update_document,
)


def get_user_by_uid(uid: str):
    return get_document(COLLECTIONS["users"], uid)


def get_event_by_id(event_id: str):
    return get_document(COLLECTIONS["events"], event_id)


def get_events_by_admin(user: Dict[str, Any]):
    allowed = set(user.get("event_ids", []))
    if not allowed:
        return query_documents(COLLECTIONS["events"])
    all_events = query_documents(COLLECTIONS["events"])
    return [e for e in all_events if e.get("event_id") in allowed or e.get("id") in allowed]


def get_registration_by_email(email: str):
    rows = query_documents(COLLECTIONS["registrations"], filters=[("email", "==", email)], limit=1)
    return rows[0] if rows else None


def create_registration(payload: Dict[str, Any], doc_id: Optional[str] = None):
    now = datetime.utcnow().isoformat()
    payload = {**payload, "created_at": payload.get("created_at", now), "updated_at": now}
    return create_document(COLLECTIONS["registrations"], payload, doc_id=doc_id)


def update_registration(registration_id: str, patch: Dict[str, Any]):
    patch = {**patch, "updated_at": datetime.utcnow().isoformat()}
    return update_document(COLLECTIONS["registrations"], registration_id, patch)


def log_access_event(payload: Dict[str, Any]):
    now = datetime.utcnow().isoformat()
    payload = {**payload, "timestamp": payload.get("timestamp", now)}
    return create_document(COLLECTIONS["access_logs"], payload)


def get_venue_by_id(venue_id: str):
    return get_document(COLLECTIONS["venues"], venue_id)
