import base64

from django.conf import settings
from django.http import HttpResponse


class AdminBasicAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        admin_host = (getattr(settings, "ADMIN_PANEL_HOST", "") or "").lower()
        if admin_host:
            host = (request.get_host().split(":")[0] or "").lower()
            if host == admin_host:
                user = getattr(settings, "ADMIN_BASIC_AUTH_USER", "") or ""
                password = getattr(settings, "ADMIN_BASIC_AUTH_PASS", "") or ""
                if not self._is_authorized(request, user, password):
                    return self._unauthorized_response()

        return self.get_response(request)

    @staticmethod
    def _is_authorized(request, user, password):
        if not user or not password:
            return False

        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Basic "):
            return False

        encoded = header.split(" ", 1)[1].strip()
        try:
            decoded = base64.b64decode(encoded).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return False

        expected = f"{user}:{password}"
        return decoded == expected

    @staticmethod
    def _unauthorized_response():
        response = HttpResponse("Authentication required", status=401)
        response["WWW-Authenticate"] = 'Basic realm="GDTA Admin"'
        return response
