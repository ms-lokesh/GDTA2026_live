import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _split_csv(value: str):
    return [v.strip() for v in value.split(",") if v.strip()]


SECRET_KEY = os.getenv("SECRET_KEY", "replace-in-production")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = _split_csv(os.getenv("ALLOWED_HOSTS", "*"))
if "*" not in ALLOWED_HOSTS:
    for local_host in ("localhost", "127.0.0.1", "0.0.0.0", "[::1]"):
        if local_host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(local_host)

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "accounts",
    "events",
    "registrations",
    "operations",
    "admin_panel",
    "communications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "middleware.logging_middleware.RequestLoggingMiddleware",
    "middleware.firebase_auth.FirebaseAuthMiddleware",
    "middleware.role_middleware.RoleEnforcementMiddleware",
    "middleware.security_headers.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    }
]

WSGI_APPLICATION = "project.wsgi.application"
ASGI_APPLICATION = "project.asgi.application"

# NOTE: Django ORM is not used. Firestore is the primary database.
# SQLite config remains only for Django framework bootstrap requirements.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "_unused.sqlite3",
    }
}

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
    "EXCEPTION_HANDLER": "core.exceptions.drf_exception_handler",
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_ROOT = BASE_DIR / "generated_ids"
MEDIA_URL = "/generated_ids/"

# Firebase
FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS", "")
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "")

# Security
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "True").lower() == "true"
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "True").lower() == "true"

# CORS allowlist
CORS_ALLOWED_ORIGINS = set(_split_csv(os.getenv("CORS_ALLOWED_ORIGINS", "")))

# Middleware auth bypass paths
PUBLIC_PATH_PREFIXES = set(
    _split_csv(
        os.getenv(
            "PUBLIC_PATH_PREFIXES",
            "/api/health,/api/registrations/start,/api/registrations/answer,/api/registrations/status,/api/registrations/cancel,/api/registrations/submit,/api/registrations/payment/create-link,/api/registrations/payment/status",
        )
    )
)

# SMTP
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "GDTA 2026 Team")

# Zoho Payments
ZOHO_CLIENT_ID = os.getenv("ZOHO_CLIENT_ID", "")
ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET", "")
ZOHO_REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN", "")
ZOHO_ORGANIZATION_ID = os.getenv("ZOHO_ORGANIZATION_ID", "")
ZOHO_ACCOUNTS_BASE_URL = os.getenv("ZOHO_ACCOUNTS_BASE_URL", "https://accounts.zoho.com")
ZOHO_BOOKS_API_BASE_URL = os.getenv("ZOHO_BOOKS_API_BASE_URL", "https://www.zohoapis.com/books/v3")
ZOHO_REDIRECT_URI = os.getenv("ZOHO_REDIRECT_URI", "")
PAYMENT_MOCK_MODE = os.getenv("PAYMENT_MOCK_MODE", "False").lower() == "true"
ADMIN_DASHBOARD_DEMO_MODE = os.getenv("ADMIN_DASHBOARD_DEMO_MODE", "False").lower() == "true"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        }
    },
    "loggers": {
        "": {"handlers": ["console"], "level": "INFO"},
    },
}
