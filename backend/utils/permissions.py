from functools import wraps

from rest_framework import status

from core.constants import ERROR_CODES
from core.response import error_response


def require_roles(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(view, request, *args, **kwargs):
            user = getattr(request, "user", None) or {}
            if user.get("role") not in set(allowed_roles):
                return error_response("Forbidden", ERROR_CODES["FORBIDDEN"], status=403)
            return fn(view, request, *args, **kwargs)

        return wrapper

    return decorator


def ensure_event_scope(request, event_id):
    user = getattr(request, "user", None) or {}
    if user.get("role") == "SUPER_ADMIN":
        return True
    allowed = set(user.get("event_ids", []))
    return event_id in allowed
