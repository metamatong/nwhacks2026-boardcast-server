from django.urls import path
from rest_framework.views import APIView
from rest_framework.response import Response


class HealthView(APIView):
    def get(self, request):
        return Response({"ok": True})


urlpatterns = [path("health/", HealthView.as_view())]
