from rest_framework.views import APIView

from core.constants import ERROR_CODES
from core.response import error_response, success_response
from utils.permissions import require_roles

from .serializers import EmailSendSerializer
from .services import send_email


class EmailSendView(APIView):
    @require_roles("SUPER_ADMIN", "ADMIN")
    def post(self, request):
        serializer = EmailSendSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)

        sent = 0
        failed = []
        for email in serializer.validated_data["to_emails"]:
            ok, err = send_email(
                to_email=email,
                subject=serializer.validated_data["subject"],
                message=serializer.validated_data["message"],
                sent_by=request.user.get("uid"),
            )
            if ok:
                sent += 1
            else:
                failed.append({"email": email, "error": err})

        return success_response({"sent": sent, "failed": failed})
