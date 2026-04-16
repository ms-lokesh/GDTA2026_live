from rest_framework.views import APIView

from core.constants import ERROR_CODES
from core.exceptions import AppError
from core.response import error_response, success_response
from utils.permissions import require_roles

from .serializers import (
    EmailSendSerializer,
    EmailTemplateSerializer,
    EmailTemplateUpdateSerializer,
)
from .services import (
    create_template,
    delete_template,
    list_templates,
    resolve_message,
    send_email,
    update_template,
)


class EmailSendView(APIView):
    @require_roles("SUPER_ADMIN", "ADMIN")
    def post(self, request):
        serializer = EmailSendSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)

        try:
            subject, message = resolve_message(
                serializer.validated_data.get("subject", ""),
                serializer.validated_data.get("message", ""),
                serializer.validated_data.get("template_id", ""),
                serializer.validated_data.get("variables", {}),
            )
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)

        sent = 0
        failed = []
        for email in serializer.validated_data["to_emails"]:
            ok, err = send_email(
                to_email=email,
                subject=subject,
                message=message,
                sent_by=request.user.get("uid"),
            )
            if ok:
                sent += 1
            else:
                failed.append({"email": email, "error": err})

        return success_response({"sent": sent, "failed": failed})


class EmailTemplateListCreateView(APIView):
    @require_roles("SUPER_ADMIN", "ADMIN")
    def get(self, _request):
        return success_response(list_templates())

    @require_roles("SUPER_ADMIN", "ADMIN")
    def post(self, request):
        serializer = EmailTemplateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)
        template = create_template(serializer.validated_data, request.user.get("uid"))
        return success_response(template, status=201)


class EmailTemplateDetailView(APIView):
    @require_roles("SUPER_ADMIN", "ADMIN")
    def put(self, request, template_id):
        serializer = EmailTemplateUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)
        try:
            out = update_template(template_id, serializer.validated_data)
            return success_response(out)
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)

    @require_roles("SUPER_ADMIN", "ADMIN")
    def delete(self, _request, template_id):
        try:
            delete_template(template_id)
            return success_response({"deleted": True})
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)
