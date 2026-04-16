from django.http import HttpResponse
from django.conf import settings
from rest_framework.views import APIView

from core.constants import ERROR_CODES, ROLE_ADMIN, ROLE_VOLUNTEER
from core.exceptions import AppError
from core.response import error_response, success_response
from utils.permissions import require_roles

from .serializers import (
    BulkStatusSerializer,
    IdCardGenerateSerializer,
    UserManagementSerializer,
    UserManagementUpdateSerializer,
)
from .services import (
    bulk_update_status,
    create_user_with_role,
    delete_user_with_role,
    export_access_logs,
    export_registrations,
    export_venues,
    generate_id_card,
    get_id_card_status,
    get_stats,
    list_registrations,
    list_users_by_role,
    update_user_with_role,
)


def _actor(request):
    user = getattr(request, "user", None) or getattr(getattr(request, "_request", None), "user", None) or {}
    req = getattr(request, "_request", None) or request
    host = (getattr(req, "get_host", lambda: "")() or "").split(":")[0]
    is_local_host = host in {"localhost", "127.0.0.1", "0.0.0.0", "[::1]"}
    path = getattr(req, "path", "")

    if (
        not user
        and getattr(settings, "ADMIN_DASHBOARD_DEMO_MODE", False)
        and is_local_host
        and path.startswith("/api/admin-panel/")
    ):
        return {
            "uid": "local-admin-demo",
            "username": "admin",
            "name": "Local Admin",
            "role": "SUPER_ADMIN",
            "assigned_events": [],
        }

    return user


class RegistrationListView(APIView):
    @require_roles("SUPER_ADMIN", "ADMIN")
    def get(self, request):
        data = list_registrations(_actor(request), request.query_params)
        return success_response(data)


class RegistrationBulkStatusView(APIView):
    @require_roles("SUPER_ADMIN", "ADMIN")
    def post(self, request):
        serializer = BulkStatusSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)

        try:
            updated = bulk_update_status(
                _actor(request),
                serializer.validated_data["registration_ids"],
                serializer.validated_data["status"],
            )
            return success_response({"updated": updated})
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)


class StatsView(APIView):
    @require_roles("SUPER_ADMIN", "ADMIN")
    def get(self, request):
        return success_response(get_stats(_actor(request)))


class ExportRegistrationsView(APIView):
    @require_roles("SUPER_ADMIN", "ADMIN")
    def get(self, request):
        payload = export_registrations(_actor(request), request.query_params)
        response = HttpResponse(payload, content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="registrations_export.csv"'
        return response


class ExportVenuesView(APIView):
    @require_roles("SUPER_ADMIN", "ADMIN")
    def get(self, request):
        payload = export_venues(_actor(request), request.query_params)
        response = HttpResponse(payload, content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="venues_export.csv"'
        return response


class ExportAccessLogsView(APIView):
    @require_roles("SUPER_ADMIN", "ADMIN")
    def get(self, request):
        payload = export_access_logs(_actor(request), request.query_params)
        response = HttpResponse(payload, content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="access_logs_export.csv"'
        return response


class IdCardGenerateView(APIView):
    @require_roles("SUPER_ADMIN", "ADMIN")
    def post(self, request, registration_id):
        serializer = IdCardGenerateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)
        try:
            out = generate_id_card(
                registration_id,
                _actor(request),
                force_regenerate=serializer.validated_data.get("force_regenerate", False),
            )
            return success_response(out)
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)


class IdCardStatusView(APIView):
    @require_roles("SUPER_ADMIN", "ADMIN")
    def get(self, request, registration_id):
        try:
            out = get_id_card_status(registration_id, _actor(request))
            return success_response(out)
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)


class VolunteerListCreateView(APIView):
    @require_roles("SUPER_ADMIN", "ADMIN")
    def get(self, request):
        return success_response(list_users_by_role(ROLE_VOLUNTEER, _actor(request)))

    @require_roles("SUPER_ADMIN")
    def post(self, request):
        serializer = UserManagementSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)
        try:
            out = create_user_with_role(ROLE_VOLUNTEER, serializer.validated_data, _actor(request))
            return success_response(out, status=201)
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)


class VolunteerDetailView(APIView):
    @require_roles("SUPER_ADMIN")
    def put(self, request, user_id):
        serializer = UserManagementUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)
        try:
            out = update_user_with_role(ROLE_VOLUNTEER, user_id, serializer.validated_data, _actor(request))
            return success_response(out)
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)

    @require_roles("SUPER_ADMIN")
    def delete(self, request, user_id):
        try:
            delete_user_with_role(ROLE_VOLUNTEER, user_id, _actor(request))
            return success_response({"deleted": True})
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)


class AdminListCreateView(APIView):
    @require_roles("SUPER_ADMIN", "ADMIN")
    def get(self, request):
        return success_response(list_users_by_role(ROLE_ADMIN, _actor(request)))

    @require_roles("SUPER_ADMIN")
    def post(self, request):
        serializer = UserManagementSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)
        try:
            out = create_user_with_role(ROLE_ADMIN, serializer.validated_data, _actor(request))
            return success_response(out, status=201)
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)


class AdminDetailView(APIView):
    @require_roles("SUPER_ADMIN")
    def put(self, request, user_id):
        serializer = UserManagementUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)
        try:
            out = update_user_with_role(ROLE_ADMIN, user_id, serializer.validated_data, _actor(request))
            return success_response(out)
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)

    @require_roles("SUPER_ADMIN")
    def delete(self, request, user_id):
        try:
            delete_user_with_role(ROLE_ADMIN, user_id, _actor(request))
            return success_response({"deleted": True})
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)
