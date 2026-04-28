from django.conf import settings
from django.http import Http404
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.template import TemplateDoesNotExist
from django.urls import include, path, re_path
from django.views.static import serve
from registrations.views import PaytmCallbackView, UnifiedPaymentCreateView, UnifiedPaymentStatusView


def health(_request):
    return JsonResponse({"success": True, "data": {"status": "ok"}, "error": None})


def home(request):
    return render(request, "index.html")


def legacy_admin_hackathon(_request):
    return redirect("/static/hackathon-registrations.html")


def html_page(request, page):
    # Check if this is a registration page and show coming soon message
    registration_pages = ['register.html', 'register-safari.html', 'register-hackathon.html']

    # Disable public chatbot pages
    disabled_pages = ["chatbot.html"]
    
    if page in registration_pages:
        return render(request, 'registration-coming-soon.html')

    if page in disabled_pages:
        raise Http404("Page not found")
    
    # Supports links like /about-gdta.html from migrated templates.
    try:
        return render(request, page)
    except TemplateDoesNotExist as exc:
        raise Http404("Page not found") from exc


urlpatterns = [
    path("", home),
    path("admin/hackathon-registrations", legacy_admin_hackathon),
    re_path(r"^(?P<page>[\w\-]+\.html)$", html_page),
    path("api/health", health),
    path("api/accounts/", include("accounts.urls")),
    path("api/events/", include("events.urls")),
    path("api/registrations/", include("registrations.urls")),
    path("api/payment/create", UnifiedPaymentCreateView.as_view()),
    path("api/payment/paytm/callback", PaytmCallbackView.as_view()),
    path("api/payment/status/<str:order_id>", UnifiedPaymentStatusView.as_view()),
    path("api/chatbot/", include("chatbot.urls")),
    path("api/hackathon/", include("hackathon.urls")),
    path("api/operations/", include("operations.urls")),
    path("api/admin-panel/", include("admin_panel.urls")),
    path("api/communications/", include("communications.urls")),
    re_path(r"^static/(?P<path>.*)$", serve, {"document_root": settings.BASE_DIR / "static"}),
    re_path(r"^generated_ids/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
