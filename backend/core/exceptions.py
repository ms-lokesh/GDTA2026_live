import logging

from rest_framework.views import exception_handler

from core.constants import ERROR_CODES

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(self, message, code=ERROR_CODES["INTERNAL_ERROR"], status_code=400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


def drf_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        message = "Request failed"
        if isinstance(response.data, dict):
            message = response.data.get("detail") or str(response.data)
        response.data = {
            "success": False,
            "data": None,
            "error": {"message": str(message), "code": ERROR_CODES["VALIDATION_ERROR"]},
        }
        return response

    logger.exception("Unhandled exception", exc_info=exc)
    from rest_framework.response import Response

    return Response(
        {
            "success": False,
            "data": None,
            "error": {
                "message": "Internal server error",
                "code": ERROR_CODES["INTERNAL_ERROR"],
            },
        },
        status=500,
    )
