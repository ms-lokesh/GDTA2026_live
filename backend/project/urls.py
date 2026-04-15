from django.http import JsonResponse
from django.urls import include, path


def health(_request):
    return JsonResponse({"success": True, "data": {"status": "ok"}, "error": None})


urlpatterns = [
    path("api/health", health),
    path("api/accounts/", include("accounts.urls")),
    path("api/events/", include("events.urls")),
    path("api/registrations/", include("registrations.urls")),
    path("api/operations/", include("operations.urls")),
    path("api/admin-panel/", include("admin_panel.urls")),
    path("api/communications/", include("communications.urls")),
]
