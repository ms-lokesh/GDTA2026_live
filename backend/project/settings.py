import json
import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=False)
load_dotenv(BASE_DIR.parent / ".env", override=True)


def _split_csv(value: str):
    return [v.strip() for v in value.split(",") if v.strip()]


CRITICAL_ENV_VARS = [
    "SECRET_KEY",
    "ALLOWED_HOSTS",
    "ZOHO_CLIENT_ID",
    "ZOHO_CLIENT_SECRET",
    "ZOHO_REFRESH_TOKEN",
    "ZOHO_ORGANIZATION_ID",
]
missing_env = [key for key in CRITICAL_ENV_VARS if not os.getenv(key)]
if missing_env:
    raise ImproperlyConfigured(f"Missing required environment variables: {', '.join(missing_env)}")

_db_url = os.getenv("DATABASE_URL", "").strip()
_db_host = os.getenv("DB_HOST", "").strip()
if not _db_url and not _db_host:
    raise ImproperlyConfigured(
        "Missing database configuration. Provide DATABASE_URL or DB_HOST/DB_NAME/DB_USER/DB_PASSWORD."
    )

SECRET_KEY = os.environ["SECRET_KEY"]
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "").split(",") if host.strip()]
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS must contain at least one host")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "axes",
    "chatbot",
    "accounts",
    "datastore",
    "events",
    "registrations",
    "operations",
    "admin_panel",
    "communications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "middleware.admin_basic_auth.AdminBasicAuthMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "axes.middleware.AxesMiddleware",
    "middleware.admin_session_timeout.AdminSessionTimeoutMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "middleware.logging_middleware.RequestLoggingMiddleware",
    "middleware.session_auth.SessionAuthMiddleware",
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
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "project.wsgi.application"
ASGI_APPLICATION = "project.asgi.application"

if _db_host:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "postgres"),
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": _db_host,
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": int(os.getenv("DATABASE_CONN_MAX_AGE", "600")),
        }
    }
else:
    DATABASES = {
        "default": dj_database_url.config(
            default=_db_url,
            conn_max_age=int(os.getenv("DATABASE_CONN_MAX_AGE", "600")),
            ssl_require=os.getenv("DATABASE_SSL_REQUIRE", "True").lower() == "true",
        )
    }

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/minute",
        "user": "100/minute",
        "login": "5/minute",
        "registration_submit": "3/minute",
        "payment_create": "10/minute",
        "chatbot": "30/minute",
        "admin_user": "100/minute",
    },
    "EXCEPTION_HANDLER": "core.exceptions.drf_exception_handler",
}

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_LOCKOUT_PARAMETERS = ["ip_address", "username"]
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = None
AXES_ENABLE_ADMIN = True

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = "/app/staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_ROOT = BASE_DIR / "generated_ids"
MEDIA_URL = "/generated_ids/"

# Security
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True").lower() == "true"
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS") or "31536000")
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = "DENY"

# Admin host basic auth
ADMIN_PANEL_HOST = os.getenv("ADMIN_PANEL_HOST", "").strip().lower()
ADMIN_BASIC_AUTH_USER = os.getenv("ADMIN_BASIC_AUTH_USER", "").strip()
ADMIN_BASIC_AUTH_PASS = os.getenv("ADMIN_BASIC_AUTH_PASS", "").strip()

_coop_value = os.getenv("SECURE_CROSS_ORIGIN_OPENER_POLICY", "")
SECURE_CROSS_ORIGIN_OPENER_POLICY = _coop_value if _coop_value else None

SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_AGE = int(os.getenv("SESSION_COOKIE_AGE", "3600"))
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
USER_SESSION_IDLE_TIMEOUT = int(os.getenv("USER_SESSION_IDLE_TIMEOUT", "7200"))
ADMIN_SESSION_IDLE_TIMEOUT = int(os.getenv("ADMIN_SESSION_IDLE_TIMEOUT", "1800"))

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Strict"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]
PASSWORD_RESET_TIMEOUT = 3600

# CORS
CORS_ALLOWED_ORIGINS = set(_split_csv(os.getenv("CORS_ALLOWED_ORIGINS", "")))

# Public paths
PUBLIC_PATH_PREFIXES = set(
    _split_csv(
        os.getenv(
            "PUBLIC_PATH_PREFIXES",
            "/api/health,/api/registrations/start,/api/registrations/answer,/api/registrations/status,/api/registrations/cancel,/api/registrations/submit,/api/registrations/payment/create-link,/api/registrations/payment/status,/api/registrations/payment/create,/api/registrations/payment/status/,/api/registrations/payment/paytm/callback,/api/payment/create,/api/payment/paytm/callback,/api/payment/status/,/api/chatbot/start,/api/chatbot/message,/api/chatbot/session,/api/chatbot/reset,/api/admin-panel/login",
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

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Registration lock
REGISTRATION_LOCKED = os.getenv("REGISTRATION_LOCKED", "False").lower() == "true"

# Zoho
ZOHO_CLIENT_ID = os.getenv("ZOHO_CLIENT_ID", "")
ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET", "")
ZOHO_REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN", "")
ZOHO_ORGANIZATION_ID = os.getenv("ZOHO_ORGANIZATION_ID", "")
ZOHO_ACCOUNTS_BASE_URL = os.getenv("ZOHO_ACCOUNTS_BASE_URL", "https://accounts.zoho.com")
ZOHO_BOOKS_API_BASE_URL = os.getenv("ZOHO_BOOKS_API_BASE_URL", "https://www.zohoapis.com/books/v3")
ZOHO_REDIRECT_URI = os.getenv("ZOHO_REDIRECT_URI", "")

# Paytm
PAYTM_MERCHANT_ID = os.getenv("PAYTM_MERCHANT_ID", "")
PAYTM_MERCHANT_KEY = os.getenv("PAYTM_MERCHANT_KEY", "")
PAYTM_WEBSITE = os.getenv("PAYTM_WEBSITE", "DEFAULT")
PAYTM_INDUSTRY_TYPE = os.getenv("PAYTM_INDUSTRY_TYPE", "Retail")
PAYTM_CALLBACK_URL = os.getenv("PAYTM_CALLBACK_URL", "")
PAYTM_ENV = os.getenv("PAYTM_ENV", "staging")

PAYMENT_USD_TO_INR_RATE = float(os.getenv("PAYMENT_USD_TO_INR_RATE", "83.0"))
PAYMENT_EXCHANGE_RATE_URL = os.getenv(
    "PAYMENT_EXCHANGE_RATE_URL",
    "https://open.er-api.com/v6/latest/USD",
)
PAYMENT_EXCHANGE_RATE_CACHE_SECONDS = int(os.getenv("PAYMENT_EXCHANGE_RATE_CACHE_SECONDS", "3600"))

ADMIN_DASHBOARD_DEMO_MODE = os.getenv("ADMIN_DASHBOARD_DEMO_MODE", "False").lower() == "true"
SUPER_ADMIN_SETUP_ENABLED = os.getenv("SUPER_ADMIN_SETUP_ENABLED", "False").lower() == "true"
SUPER_ADMIN_SETUP_ALLOWED_IPS = set(_split_csv(os.getenv("SUPER_ADMIN_SETUP_ALLOWED_IPS", "")))
if SUPER_ADMIN_SETUP_ENABLED:
    PUBLIC_PATH_PREFIXES.add("/api/super-admin-setup")
PUBLIC_PATH_PREFIXES.add("/api/registrations/payment/paytm/initiate")
DJANGO_ADMIN_URL = os.getenv("DJANGO_ADMIN_URL", "")
if DJANGO_ADMIN_URL and not DJANGO_ADMIN_URL.endswith("/"):
    DJANGO_ADMIN_URL += "/"
CONSENT_VERSION = os.getenv("CONSENT_VERSION", "2026-05-02")
CONSENT_TEXT = os.getenv(
    "CONSENT_TEXT",
    "I consent to GDTA 2026 processing my registration details for event participation and payment administration.",
)

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
