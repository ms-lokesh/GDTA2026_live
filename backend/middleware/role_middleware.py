from django.http import JsonResponse

from core.constants import ERROR_CODES, ROLE_ADMIN, ROLE_SUPER_ADMIN, ROLE_VOLUNTEER


def _forbidden(message="Forbidden"):
    return JsonResponse(
        {
            "success": False,
            "data": None,
            "error": {"message": message, "code": ERROR_CODES["FORBIDDEN"]},
        },
        status=403,
    )


class RoleEnforcementMiddleware:
    """
    Baseline role controls at middleware layer.
    Fine-grained event scoping is additionally enforced in decorators/services.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is None:
            return self.get_response(request)

        role = user.get("role")
        path = request.path

        if path.startswith("/api/superadmin/") and role != ROLE_SUPER_ADMIN:
            return _forbidden("Super admin access required")

        if path.startswith("/api/admin-panel/") and role not in {ROLE_SUPER_ADMIN, ROLE_ADMIN}:
            return _forbidden("Admin access required")

        if path.startswith("/api/operations/qr") and role not in {ROLE_VOLUNTEER, ROLE_ADMIN, ROLE_SUPER_ADMIN}:
            return _forbidden("Volunteer/Admin access required")

        return self.get_response(request)
