from functools import wraps

from django.conf import settings
from rest_framework import status

from core.constants import ERROR_CODES
from core.exceptions import AppError
from core.response import error_response


def require_roles(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(view, request, *args, **kwargs):
            user = (
                getattr(request, "user", None)
                or getattr(getattr(request, "_request", None), "user", None)
                or {}
            )

            req = getattr(request, "_request", None) or request
            host = (getattr(req, "get_host", lambda: "")() or "").split(":")[0]
            is_local_host = host in {"localhost", "127.0.0.1", "0.0.0.0", "[::1]"}
            path = getattr(req, "path", "")

            if (
                not user
                and getattr(settings, "ADMIN_DASHBOARD_DEMO_MODE", False)
                and is_local_host
                and (path.startswith("/api/admin-panel/") or path.startswith("/api/hackathon/"))
            ):
                user = {"role": "SUPER_ADMIN"}

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


def assert_event_scope(user, event_id):
    if user.get("role") == "SUPER_ADMIN":
        return True
    allowed = set(user.get("event_ids", []))
    if event_id not in allowed:
        raise AppError("Cross-event access denied", ERROR_CODES["FORBIDDEN"], 403)
    return True


def is_admin_role(user):
    return (user or {}).get("role") in {"SUPER_ADMIN", "ADMIN"}
