import logging

from django.conf import settings
from django.http import JsonResponse

from accounts.models import UserProfile
from core.constants import ERROR_CODES

logger = logging.getLogger(__name__)


def _auth_error(message="Unauthorized", status=401):
    return JsonResponse(
        {
            "success": False,
            "data": None,
            "error": {"message": message, "code": ERROR_CODES["UNAUTHORIZED"]},
        },
        status=status,
    )


def _serialize_user(user):
    profile = getattr(user, "profile", None)
    if not profile:
        return {
            "uid": user.username,
            "id": user.username,
            "username": user.username,
            "name": user.get_full_name() or user.username,
            "email": user.email,
            "role": None,
            "event_ids": [],
            "assigned_events": [],
            "assigned_venues": [],
            "is_active": user.is_active,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }
    return profile.as_payload()


class SessionAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.user = getattr(request, "user", None)

        host = (request.get_host() or "").split(":")[0]
        is_local_host = host in {"localhost", "127.0.0.1", "0.0.0.0", "[::1]"}

        if not request.path.startswith("/api/"):
            return self.get_response(request)

        for prefix in settings.PUBLIC_PATH_PREFIXES:
            if request.path.startswith(prefix):
                return self.get_response(request)

        if (
            getattr(settings, "ADMIN_DASHBOARD_DEMO_MODE", False)
            and is_local_host
            and request.path.startswith("/api/admin-panel/")
        ):
            request.user = {
                "uid": "local-admin-demo",
                "username": "admin",
                "name": "Local Admin",
                "role": "ADMIN",
                "is_active": True,
                "event_ids": [],
                "assigned_events": [],
                "assigned_venues": [],
            }
            return self.get_response(request)

        django_user = getattr(request, "user", None)
        if not getattr(django_user, "is_authenticated", False):
            logger.warning("Auth failure: missing session path=%s", request.path)
            return _auth_error()

        payload = _serialize_user(django_user)
        if not payload.get("is_active", True):
            return _auth_error()

        request.user = payload
        return self.get_response(request)
