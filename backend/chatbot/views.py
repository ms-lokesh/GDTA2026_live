from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from chatbot.serializers import ChatbotMessageSerializer, ChatbotSessionSerializer, ChatbotStartSerializer
from chatbot.services import get_chat_session, process_chat_message, reset_chat_session, start_chat_session
from core.constants import ERROR_CODES
from core.exceptions import AppError
from core.response import error_response, success_response
from utils.throttles import ChatbotRateThrottle


class ChatbotStartView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ChatbotRateThrottle]

    def post(self, request):
        serializer = ChatbotStartSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)
        data = start_chat_session(serializer.validated_data.get("mode", "conference_registration"))
        return success_response(data, status=201)


class ChatbotMessageView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ChatbotRateThrottle]

    def post(self, request):
        serializer = ChatbotMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)
        try:
            data = process_chat_message(
                session_id=serializer.validated_data["session_id"],
                message=serializer.validated_data["message"],
            )
            return success_response(data)
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)


class ChatbotSessionView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ChatbotRateThrottle]

    def get(self, request):
        serializer = ChatbotSessionSerializer(data=request.query_params)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)
        try:
            session = get_chat_session(serializer.validated_data["session_id"])
            return success_response(session)
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)


class ChatbotResetView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ChatbotRateThrottle]

    def post(self, request):
        serializer = ChatbotSessionSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)
        try:
            data = reset_chat_session(serializer.validated_data["session_id"])
            return success_response(data)
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)
