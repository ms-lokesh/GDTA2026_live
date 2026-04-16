from rest_framework.views import APIView

from core.constants import ERROR_CODES
from core.exceptions import AppError
from core.response import error_response, success_response
from operations.serializers import QRValidateSerializer, VenueSerializer
from operations.services import create_venue, delete_venue, list_venues, update_venue, validate_qr
from utils.permissions import require_roles


class VenueListCreateView(APIView):
    @require_roles("SUPER_ADMIN", "ADMIN")
    def get(self, request):
        return success_response(list_venues(request.user))

    @require_roles("SUPER_ADMIN", "ADMIN")
    def post(self, request):
        serializer = VenueSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)
        venue_id = create_venue(serializer.validated_data, request.user)
        return success_response({"venue_id": venue_id}, status=201)


class VenueDetailView(APIView):
    @require_roles("SUPER_ADMIN", "ADMIN")
    def put(self, request, venue_id):
        serializer = VenueSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)
        update_venue(venue_id, serializer.validated_data, request.user)
        return success_response({"venue_id": venue_id})

    @require_roles("SUPER_ADMIN", "ADMIN")
    def delete(self, request, venue_id):
        delete_venue(venue_id, request.user)
        return success_response({"deleted": True})


class QRValidateView(APIView):
    @require_roles("SUPER_ADMIN", "ADMIN", "VOLUNTEER")
    def post(self, request):
        serializer = QRValidateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)
        try:
            data = validate_qr(
                serializer.validated_data["unique_id"],
                serializer.validated_data["venue_id"],
                scanned_by=request.user.get("uid"),
            )
            return success_response(data)
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)
