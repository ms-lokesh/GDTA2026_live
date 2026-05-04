from django.conf import settings
from django.http import JsonResponse


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get("Origin", "").strip()

        if request.method == "OPTIONS":
            response = JsonResponse({"success": True, "data": {}, "error": None})
        else:
            response = self.get_response(request)

        if origin and settings.CORS_ALLOWED_ORIGINS and origin in settings.CORS_ALLOWED_ORIGINS:
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Credentials"] = "true"
            response["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
            response["Access-Control-Allow-Headers"] = "Authorization,Content-Type"

        # Allow same-origin iframe embeds (used by chatbot widget iframe)
        # while still blocking external origins.
        response["X-Frame-Options"] = "SAMEORIGIN"
        response["X-Content-Type-Options"] = "nosniff"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Keep production strict, but allow development UI dependencies (CDNs + inline blocks)
        # for local-host runs (even if DEBUG=False in env).
        host = (request.get_host() or "").split(":")[0]
        is_local_host = host in {"localhost", "127.0.0.1", "0.0.0.0", "[::1]"}

        if settings.DEBUG or is_local_host:
            csp_policy = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://code.jquery.com https://cdn.jsdelivr.net https://cdn.datatables.net https://cdn.tailwindcss.com https://www.googletagmanager.com https://www.google-analytics.com https://connect.facebook.net; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://cdn.datatables.net; "
                "font-src 'self' data: https://fonts.gstatic.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
                "img-src 'self' data: blob: https:; "
                "connect-src 'self' https: https://www.google-analytics.com https://stats.g.doubleclick.net https://connect.facebook.net; "
                "frame-src 'self' https://www.google.com https://maps.google.com https://www.facebook.com; "
                "frame-ancestors 'self'; base-uri 'self'; form-action 'self' https://securegw.paytm.in https://securegw-stage.paytm.in https://www.facebook.com https://www.google-analytics.com https://www.googletagmanager.com"
            )
        else:
            csp_policy = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://code.jquery.com https://cdn.jsdelivr.net https://cdn.datatables.net https://cdn.tailwindcss.com https://www.googletagmanager.com https://www.google-analytics.com https://connect.facebook.net; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://cdn.datatables.net; "
                "img-src 'self' data: blob: https:; "
                "font-src 'self' data: https://fonts.gstatic.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
                "connect-src 'self' https: https://www.google-analytics.com https://stats.g.doubleclick.net https://connect.facebook.net; "
                "frame-src 'self' https://www.google.com https://maps.google.com https://www.facebook.com; "
                "frame-ancestors 'self'; base-uri 'self'; form-action 'self' https://securegw.paytm.in https://securegw-stage.paytm.in https://www.facebook.com https://www.google-analytics.com https://www.googletagmanager.com"
            )

        response["Content-Security-Policy"] = csp_policy

        # HSTS should not be sent for local development hosts, otherwise browsers can
        # upgrade local HTTP requests to HTTPS and cause connection failures.
        if not is_local_host:
            response["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        return response
