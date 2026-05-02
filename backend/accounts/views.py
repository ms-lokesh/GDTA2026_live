import time

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import Http404
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from accounts.models import UserProfile
from core.constants import ERROR_CODES, ROLE_ADMIN, ROLE_VOLUNTEER
from core.response import error_response, success_response
from utils.throttles import LoginRateThrottle


GENERIC_ADMIN_AUTH_ERROR = "Unable to complete this request"


def _constant_delay(started_at, minimum_seconds=0.35):
    remaining = minimum_seconds - (time.monotonic() - started_at)
    if remaining > 0:
        time.sleep(remaining)


class MeView(APIView):
    def get(self, request):
        return success_response(request.user)


class AdminLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        started_at = time.monotonic()
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        if not username or not password:
            _constant_delay(started_at)
            return error_response("Username and password required", ERROR_CODES["VALIDATION_ERROR"], 400)

        user = authenticate(request, username=username, password=password)
        if not user or not user.is_active:
            _constant_delay(started_at)
            return error_response("Invalid credentials", ERROR_CODES["UNAUTHORIZED"], 401)

        try:
            profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            UserProfile.objects.create(
                user=user,
                role=ROLE_VOLUNTEER,
                name=user.get_full_name() or user.username,
                is_active=False,
            )
            _constant_delay(started_at)
            return error_response(GENERIC_ADMIN_AUTH_ERROR, ERROR_CODES["FORBIDDEN"], 403)

        if not (user.is_staff and profile.role == ROLE_ADMIN and profile.is_active):
            _constant_delay(started_at)
            return error_response(GENERIC_ADMIN_AUTH_ERROR, ERROR_CODES["FORBIDDEN"], 403)

        login(request, user)
        return success_response({"user": profile.as_payload()})


class AdminLogoutView(APIView):
    def post(self, request):
        logout(request)
        return success_response({"logged_out": True})


class AdminMeView(APIView):
    def get(self, request):
        user = request.user
        if not user:
            return error_response("Unauthorized", ERROR_CODES["UNAUTHORIZED"], 401)
        return success_response({"user": user})


class SuperAdminSetupView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        if not getattr(settings, "SUPER_ADMIN_SETUP_ENABLED", False):
            raise Http404("Page not found")

        User = get_user_model()
        if User.objects.filter(is_superuser=True).exists() or UserProfile.objects.filter(role=ROLE_ADMIN).exists():
            raise Http404("Page not found")

        remote_addr = request.META.get("REMOTE_ADDR", "")
        allowed_ips = getattr(settings, "SUPER_ADMIN_SETUP_ALLOWED_IPS", set())
        if not allowed_ips or remote_addr not in allowed_ips:
            raise Http404("Page not found")

        username = (request.data.get("username") or "").strip()
        name = (request.data.get("name") or "").strip()
        email = (request.data.get("email") or "").strip()
        password = request.data.get("password") or ""

        if not username or not name or not email or not password:
            return error_response("All fields are required", ERROR_CODES["VALIDATION_ERROR"], 400)

        if User.objects.filter(username=username).exists():
            return success_response({"message": "Setup request received"})

        try:
            validate_password(password)
        except ValidationError:
            return success_response({"message": "Setup request received"})

        user = User.objects.create(
            username=username,
            email=email,
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )
        user.set_password(password)
        user.save()

        UserProfile.objects.create(
            user=user,
            role=ROLE_ADMIN,
            name=name,
            is_active=True,
        )

        return success_response({"message": "Setup request received"}, status=201)
