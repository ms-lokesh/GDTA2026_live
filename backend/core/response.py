from rest_framework.response import Response


def success_response(data=None, status=200):
    return Response({"success": True, "data": data or {}, "error": None}, status=status)


def error_response(message, code, status=400):
    return Response(
        {
            "success": False,
            "data": None,
            "error": {"message": message, "code": code},
        },
        status=status,
    )
