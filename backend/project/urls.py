from django.conf import settings
from django.contrib import admin
from django.http import Http404
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.template import TemplateDoesNotExist
from django.urls import include, path, re_path
from django.views.static import serve
from registrations.views import AdminUnifiedPaymentStatusView, PaytmCallbackView, UnifiedPaymentCreateView, UnifiedPaymentStatusView
from accounts.views import AdminLoginView, AdminLogoutView, AdminMeView, SuperAdminSetupView


def health(_request):
    return JsonResponse({"status": "ok"})


def home(request):
    return render(request, "index.html")


def index_redirect(_request):
    return redirect("/", permanent=True)


def admin_dashboard_redirect(_request):
    raise Http404("Page not found")


def not_found(_request):
    raise Http404("Page not found")


def staff_static_page(request, path):
    if not getattr(request.user, "is_staff", False):
        raise Http404("Page not found")
    return serve(request, path, document_root=settings.BASE_DIR / "static")


PAGE_MAP = {
    "about-gdta": "about-gdta.html",
    "about-gdta-2026": "about-gdta-2026.html",
    "about-sns": "about-sns.html",
    "contact": "contact.html",
    "hackathon": "hackathon.html",
    "program-schedule": "program-schedule.html",
    "program-sessions": "program-sessions.html",
    "program-safari": "program-safari.html",
    "register": "register.html",
    "register-safari": "register-safari.html",
    "register-hackathon": "register-hackathon.html",
    "sponsors": "sponsors.html",
    "travel-stay": "travel-stay.html",
    "code": "code.html",
    "privacy-policy": "privacy-policy.html",
    "terms-and-conditions": "terms-and-conditions.html",
}

DISABLED_SLUGS = {"chatbot"}


def clean_page(request, page):
    if page in DISABLED_SLUGS:
        raise Http404("Page not found")

    template_name = PAGE_MAP.get(page)
    if not template_name:
        raise Http404("Page not found")

    try:
        return render(request, template_name)
    except TemplateDoesNotExist as exc:
        raise Http404("Page not found") from exc


def html_page(_request, page):
    slug = page[:-5]
    return redirect(f"/{slug}", permanent=True)


urlpatterns = [
    path("", home),
    path("home", home),
    path("index", index_redirect),
    path("admin/", not_found),
    path("django-admin/", not_found),
    path("about-gdta", clean_page, {"page": "about-gdta"}),
    path("about-gdta-2026", clean_page, {"page": "about-gdta-2026"}),
    path("about-sns", clean_page, {"page": "about-sns"}),
    path("contact", clean_page, {"page": "contact"}),
    path("hackathon", clean_page, {"page": "hackathon"}),
    path("program-schedule", clean_page, {"page": "program-schedule"}),
    path("program-sessions", clean_page, {"page": "program-sessions"}),
    path("program-safari", clean_page, {"page": "program-safari"}),
    path("register", clean_page, {"page": "register"}),
    path("register-safari", clean_page, {"page": "register-safari"}),
    path("register-hackathon", clean_page, {"page": "register-hackathon"}),
    path("sponsors", clean_page, {"page": "sponsors"}),
    path("travel-stay", clean_page, {"page": "travel-stay"}),
    path("code", clean_page, {"page": "code"}),
    path("privacy-policy", clean_page, {"page": "privacy-policy"}),
    path("terms-and-conditions", clean_page, {"page": "terms-and-conditions"}),
    re_path(r"^(?P<page>[\w\-]+\.html)$", html_page),
    path("api/health", health),
    path("api/admin-panel/login", AdminLoginView.as_view()),
    path("api/admin-panel/logout", AdminLogoutView.as_view()),
    path("api/admin-panel/me", AdminMeView.as_view()),
    path("api/accounts/", include("accounts.urls")),
    path("api/events/", include("events.urls")),
    path("api/registrations/", include("registrations.urls")),
    path("api/payment/create", UnifiedPaymentCreateView.as_view()),
    path("api/payment/paytm/callback", PaytmCallbackView.as_view()),
    path("api/payment/status/<str:order_id>", UnifiedPaymentStatusView.as_view()),
    path("api/admin-panel/payment/status/<str:order_id>", AdminUnifiedPaymentStatusView.as_view()),
    path("api/chatbot/", include("chatbot.urls")),
    path("api/operations/", include("operations.urls")),
    path("api/admin-panel/", include("admin_panel.urls")),
    path("api/communications/", include("communications.urls")),
    path("robots.txt", serve, {"document_root": settings.BASE_DIR / "static", "path": "robots.txt"}),
    path("admin-dashboard/", staff_static_page, {"path": "admin-dashboard.html"}),
    path("super-admin-setup/", staff_static_page, {"path": "super-admin-setup.html"}),
    re_path(r"^generated_ids/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]

if getattr(settings, "DJANGO_ADMIN_URL", ""):
    urlpatterns.insert(4, path(settings.DJANGO_ADMIN_URL, admin.site.urls))

if getattr(settings, "SUPER_ADMIN_SETUP_ENABLED", False):
    urlpatterns.append(path("api/super-admin-setup", SuperAdminSetupView.as_view()))
