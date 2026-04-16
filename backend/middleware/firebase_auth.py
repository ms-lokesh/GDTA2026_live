import logging

from django.conf import settings
from django.http import JsonResponse

from core.constants import ERROR_CODES
from services.firebase.auth import get_user_from_firestore, verify_firebase_token

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


class FirebaseAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.user = None

        host = (request.get_host() or "").split(":")[0]
        is_local_host = host in {"localhost", "127.0.0.1", "0.0.0.0", "[::1]"}

        # Public site assets/pages are not API-protected.
        if not request.path.startswith("/api/"):
            return self.get_response(request)

        # Local dashboard demo mode: allow admin panel APIs without Bearer token.
        if (
            getattr(settings, "ADMIN_DASHBOARD_DEMO_MODE", False)
            and is_local_host
            and (request.path.startswith("/api/admin-panel/") or request.path.startswith("/api/hackathon/"))
        ):
            request.user = {
                "uid": "local-admin-demo",
                "username": "admin",
                "name": "Local Admin",
                "role": "SUPER_ADMIN",
                "is_active": True,
                "assigned_events": [],
            }
            return self.get_response(request)

        for prefix in settings.PUBLIC_PATH_PREFIXES:
            if request.path.startswith(prefix):
                return self.get_response(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            logger.warning("Auth failure: missing bearer token path=%s", request.path)
            return _auth_error()

        token = auth_header.replace("Bearer ", "", 1).strip()
        if not token:
            logger.warning("Auth failure: empty token path=%s", request.path)
            return _auth_error()

        decoded = verify_firebase_token(token)
        if not decoded:
            logger.warning("Auth failure: invalid token path=%s", request.path)
            return _auth_error()

        uid = decoded.get("uid")
        user = get_user_from_firestore(uid)
        if not user:
            logger.warning("Auth failure: user inactive/not found uid=%s", uid)
            return _auth_error()

        request.user = user
        return self.get_response(request)
