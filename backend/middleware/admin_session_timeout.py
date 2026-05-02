import time

from django.conf import settings
from django.contrib.auth import logout


class AdminSessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if getattr(user, "is_authenticated", False):
            now = int(time.time())
            timeout = (
                getattr(settings, "ADMIN_SESSION_IDLE_TIMEOUT", 1800)
                if getattr(user, "is_staff", False)
                else getattr(settings, "USER_SESSION_IDLE_TIMEOUT", 7200)
            )
            last_seen = request.session.get("last_activity_at")
            if last_seen and now - int(last_seen) > int(timeout):
                logout(request)
            else:
                request.session["last_activity_at"] = now
                request.session.set_expiry(int(timeout))
        return self.get_response(request)
