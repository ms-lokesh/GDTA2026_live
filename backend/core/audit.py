from datetime import datetime
from typing import Any, Dict

from core.constants import COLLECTIONS
from services.firebase.firestore import create_document


def write_audit_log(action: str, actor_uid: str, target: Dict[str, Any] | None = None, details: Dict[str, Any] | None = None):
    payload = {
        "action": action,
        "actor_uid": actor_uid,
        "target": target or {},
        "details": details or {},
        "timestamp": datetime.utcnow().isoformat(),
    }
    return create_document(COLLECTIONS["audit_logs"], payload)
