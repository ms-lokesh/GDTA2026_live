import logging
import time

logger = logging.getLogger("request")


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        response = self.get_response(request)
        elapsed_ms = int((time.time() - start) * 1000)
        uid = None
        user = getattr(request, "user", None)
        if isinstance(user, dict):
            uid = user.get("uid")
        logger.info(
            "method=%s path=%s status=%s duration_ms=%s uid=%s",
            request.method,
            request.path,
            getattr(response, "status_code", 0),
            elapsed_ms,
            uid,
        )
        return response
