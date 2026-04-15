from rest_framework.views import APIView

from core.response import success_response


class MeView(APIView):
    def get(self, request):
        return success_response(request.user)
