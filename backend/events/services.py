from datetime import datetime

from core.constants import COLLECTIONS
from services.firebase.firestore import create_document, get_document, query_documents, update_document


def list_events_for_user(user):
    all_events = query_documents(COLLECTIONS["events"])
    if user.get("role") == "SUPER_ADMIN":
        return all_events
    allowed = set(user.get("event_ids", []))
    return [e for e in all_events if e.get("event_id") in allowed or e.get("id") in allowed]


def create_event(payload, created_by):
    payload = {
        **payload,
        "created_by": created_by,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    return create_document(COLLECTIONS["events"], payload, doc_id=payload["event_id"])


def update_event(event_id, payload):
    payload = {**payload, "updated_at": datetime.utcnow().isoformat()}
    return update_document(COLLECTIONS["events"], event_id, payload)


def delete_event(event_id):
    from services.firebase.firestore import get_collection

    get_collection(COLLECTIONS["events"]).document(event_id).delete()
    return True


def get_event(event_id):
    return get_document(COLLECTIONS["events"], event_id)
