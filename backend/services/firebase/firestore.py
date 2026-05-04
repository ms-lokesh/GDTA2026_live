import uuid
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction

from datastore.models import Document


def get_document(collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
    try:
        doc = Document.objects.get(collection=collection, doc_id=doc_id)
    except Document.DoesNotExist:
        return None
    data = dict(doc.data or {})
    data["id"] = doc.doc_id
    return data


def create_document(collection: str, data: Dict[str, Any], doc_id: Optional[str] = None) -> str:
    target_id = doc_id or uuid.uuid4().hex
    with transaction.atomic():
        doc, created = Document.objects.get_or_create(
            collection=collection,
            doc_id=target_id,
            defaults={"data": dict(data or {})},
        )
        if not created:
            doc.data = dict(data or {})
            doc.save(update_fields=["data", "updated_at"])
    return target_id


def update_document(collection: str, doc_id: str, data: Dict[str, Any]) -> bool:
    with transaction.atomic():
        doc, _created = Document.objects.get_or_create(
            collection=collection,
            doc_id=doc_id,
            defaults={"data": {}},
        )
        payload = dict(doc.data or {})
        payload.update(data or {})
        doc.data = payload
        doc.save(update_fields=["data", "updated_at"])
    return True


def delete_document(collection: str, doc_id: str) -> bool:
    Document.objects.filter(collection=collection, doc_id=doc_id).delete()
    return True


def query_documents(
    collection: str,
    filters: Optional[List[Tuple[str, str, Any]]] = None,
    limit: Optional[int] = None,
):
    qs = Document.objects.filter(collection=collection)
    for field_name, op, value in filters or []:
        if op != "==":
            continue
        qs = qs.filter(**{f"data__{field_name}": value})
    if limit:
        qs = qs[:limit]
    result = []
    for doc in qs:
        payload = dict(doc.data or {})
        payload["id"] = doc.doc_id
        result.append(payload)
    return result