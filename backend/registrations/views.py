from rest_framework.views import APIView

from core.constants import ERROR_CODES
from core.exceptions import AppError
from core.response import error_response, success_response
from registrations.serializers import (
    AnswerRegistrationSerializer,
    CancelRegistrationSerializer,
    StartRegistrationSerializer,
    SubmitRegistrationSerializer,
)
from registrations.services import (
    answer_registration,
    cancel_registration,
    get_session,
    start_registration,
    submit_registration,
)


class RegistrationStartView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = StartRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)
        data = start_registration(serializer.validated_data.get("session_id"))
        return success_response(data, status=201)


class RegistrationAnswerView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = AnswerRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)
        try:
            data = answer_registration(
                serializer.validated_data["session_id"],
                serializer.validated_data["answer"],
            )
            return success_response(data)
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)


class RegistrationStatusView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        session_id = request.query_params.get("session_id")
        if not session_id:
            return error_response("session_id required", ERROR_CODES["VALIDATION_ERROR"], 400)
        try:
            return success_response(get_session(session_id))
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)


class RegistrationCancelView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = CancelRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)
        try:
            cancel_registration(serializer.validated_data["session_id"])
            return success_response({"cancelled": True})
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)


class RegistrationSubmitView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = SubmitRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)
        try:
            out = submit_registration(serializer.validated_data)
            return success_response(out, status=201)
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)
