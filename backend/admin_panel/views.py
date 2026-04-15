from rest_framework.views import APIView

from core.constants import ERROR_CODES
from core.response import error_response, success_response
from utils.permissions import require_roles

from .serializers import BulkStatusSerializer
from .services import bulk_update_status, get_stats, list_registrations


class RegistrationListView(APIView):
    @require_roles("SUPER_ADMIN", "ADMIN")
    def get(self, request):
        data = list_registrations(request.user, request.query_params)
        return success_response(data)


class RegistrationBulkStatusView(APIView):
    @require_roles("SUPER_ADMIN", "ADMIN")
    def post(self, request):
        serializer = BulkStatusSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)

        updated = bulk_update_status(
            serializer.validated_data["registration_ids"],
            serializer.validated_data["status"],
        )
        return success_response({"updated": updated})


class StatsView(APIView):
    @require_roles("SUPER_ADMIN", "ADMIN")
    def get(self, request):
        return success_response(get_stats(request.user))
