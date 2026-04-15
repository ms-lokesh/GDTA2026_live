import json
import logging
import threading
from typing import Any, Dict, List, Optional, Tuple

import firebase_admin
from django.conf import settings
from firebase_admin import credentials, firestore

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_db = None


def _init_firebase_app():
    try:
        firebase_admin.get_app()
        return
    except ValueError:
        pass

    cred = None
    if settings.FIREBASE_CREDENTIALS:
        payload = json.loads(settings.FIREBASE_CREDENTIALS)
        cred = credentials.Certificate(payload)
    elif settings.FIREBASE_CREDENTIALS_PATH:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    else:
        raise RuntimeError("Firebase credentials are not configured")

    firebase_admin.initialize_app(cred)


def get_db_client():
    global _db
    if _db is not None:
        return _db

    with _lock:
        if _db is None:
            _init_firebase_app()
            _db = firestore.client()
    return _db


def get_collection(name: str):
    return get_db_client().collection(name)


def get_document(collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
    doc = get_collection(collection).document(doc_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict() or {}
    data["id"] = doc.id
    return data


def create_document(collection: str, data: Dict[str, Any], doc_id: Optional[str] = None) -> str:
    col = get_collection(collection)
    if doc_id:
        col.document(doc_id).set(data)
        return doc_id
    ref = col.document()
    ref.set(data)
    return ref.id


def update_document(collection: str, doc_id: str, data: Dict[str, Any]) -> bool:
    get_collection(collection).document(doc_id).set(data, merge=True)
    return True


def query_documents(collection: str, filters: Optional[List[Tuple[str, str, Any]]] = None, limit: Optional[int] = None):
    query = get_collection(collection)
    for field_name, op, value in filters or []:
        query = query.where(field_name, op, value)
    if limit:
        query = query.limit(limit)
    docs = query.stream()
    result = []
    for doc in docs:
        payload = doc.to_dict() or {}
        payload["id"] = doc.id
        result.append(payload)
    return result
