import secrets
import string
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.conf import settings
from .models import Room
from .serializers import RoomCreateSerializer, RoomJoinSerializer
from .turn import generate_turn_credentials
from .janus import JanusError, create_videoroom


class RoomCreateView(APIView):
    def post(self, request):
        title = request.data.get("title", "")
        alphabet = string.ascii_uppercase + string.digits
        join_code = "".join(secrets.choice(alphabet) for _ in range(6))
        if not settings.JANUS_URL:
            return Response(
                {"detail": "Janus URL not configured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            janus_room_id = create_videoroom(description=title or "Room")
        except JanusError as exc:
            return Response(
                {"detail": "Janus room creation failed", "error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        room = Room.objects.create(
            title=title,
            join_code=join_code,
            janus_room_id=janus_room_id,
        )
        data = RoomCreateSerializer(room).data
        data["janus_url"] = settings.JANUS_PUBLIC_URL
        return Response(data, status=status.HTTP_201_CREATED)


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

        if not room.janus_room_id:
            return Response(
                {"detail": "Janus room not configured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "room_id": str(room.id),
                "title": room.title,
                "janus_room_id": room.janus_room_id,
                "janus_url": settings.JANUS_PUBLIC_URL,
            }
        )


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
