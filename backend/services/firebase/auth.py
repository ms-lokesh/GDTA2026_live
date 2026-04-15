import logging

from firebase_admin import auth as firebase_auth

from core.constants import ALLOWED_ROLES, COLLECTIONS
from services.firebase.firestore import get_document

logger = logging.getLogger(__name__)


def verify_firebase_token(token: str):
    try:
        decoded = firebase_auth.verify_id_token(token, check_revoked=True)
        return decoded
    except Exception:
        return None


def get_user_from_firestore(uid: str):
    if not uid:
        return None

    user = get_document(COLLECTIONS["users"], uid)
    if not user:
        return None

    if not user.get("is_active", False):
        return None

    role = user.get("role")
    if role not in ALLOWED_ROLES:
        logger.warning("Invalid role for uid=%s role=%s", uid, role)
        return None

    return {
        "uid": uid,
        "role": role,
        "event_ids": user.get("event_ids", []),
        "email": user.get("email"),
        "name": user.get("name"),
    }
