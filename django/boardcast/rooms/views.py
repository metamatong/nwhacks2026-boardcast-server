import secrets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.conf import settings
from .models import Room
from .serializers import RoomCreateSerializer, RoomJoinSerializer
from .turn import generate_turn_credentials


class RoomCreateView(APIView):
    def post(self, request):
        title = request.data.get("title", "")
        join_code = secrets.token_hex(4)
        room = Room.objects.create(title=title, join_code=join_code)
        return Response(RoomCreateSerializer(room).data, status=status.HTTP_201_CREATED)


class RoomJoinView(APIView):
    def post(self, request):
        s = RoomJoinSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        room_id = s.validated_data["room_id"]
        join_code = s.validated_data.get("join_code", "")

        try:
            room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            return Response({"detail": "Room not found"}, status=status.HTTP_404_NOT_FOUND)

        # MVP: optional enforcement (enforce if join_code set)
        if room.join_code and join_code != room.join_code:
            return Response({"detail": "Invalid join code"}, status=status.HTTP_403_FORBIDDEN)

        return Response({"room_id": str(room.id), "title": room.title})


class IceConfigView(APIView):
    """
    Clients call this before creating RTCPeerConnection to get STUN/TURN servers.
    """

    def get(self, request):
        identity = request.headers.get("X-Client-Id", "guest")
        u, p = generate_turn_credentials(identity=identity)

        host = settings.TURN_HOST
        port = settings.TURN_PORT

        return Response({
            "iceServers": [
                {"urls": [f"stun:{host}:{port}"]},
                {
                    "urls": [
                        f"turn:{host}:{port}?transport=udp",
                        f"turn:{host}:{port}?transport=tcp",
                    ],
                    "username": u,
                    "credential": p,
                },
            ]
        })
