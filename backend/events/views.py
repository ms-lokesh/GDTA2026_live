from rest_framework.views import APIView

from core.constants import ERROR_CODES, ROLE_ADMIN
from core.response import error_response, success_response
from events.serializers import EventSerializer
from events.services import create_event, delete_event, get_event, list_events_for_user, update_event
from utils.permissions import ensure_event_scope


class EventListCreateView(APIView):
    def get(self, request):
        return success_response(list_events_for_user(request.user))

    def post(self, request):
        if request.user.get("role") != ROLE_ADMIN:
            return error_response("Forbidden", ERROR_CODES["FORBIDDEN"], status=403)

        serializer = EventSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], status=400)

        event_id = create_event(serializer.validated_data, created_by=request.user.get("uid"))
        return success_response({"event_id": event_id}, status=201)


class EventDetailView(APIView):
    def put(self, request, event_id):
        if request.user.get("role") != ROLE_ADMIN and not ensure_event_scope(request, event_id):
            return error_response("Forbidden", ERROR_CODES["FORBIDDEN"], status=403)

        serializer = EventSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], status=400)

        update_event(event_id, serializer.validated_data)
        return success_response({"event_id": event_id})

    def delete(self, request, event_id):
        if request.user.get("role") != ROLE_ADMIN:
            return error_response("Forbidden", ERROR_CODES["FORBIDDEN"], status=403)
        delete_event(event_id)
        return success_response({"deleted": True})

    def get(self, request, event_id):
        if request.user.get("role") != ROLE_ADMIN and not ensure_event_scope(request, event_id):
            return error_response("Forbidden", ERROR_CODES["FORBIDDEN"], status=403)
        event = get_event(event_id)
        if not event:
            return error_response("Not found", ERROR_CODES["NOT_FOUND"], status=404)
        return success_response(event)
