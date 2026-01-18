from rest_framework import serializers
from .models import Room


class RoomCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["id", "title", "join_code", "janus_room_id", "created_at"]
        read_only_fields = ["id", "janus_room_id", "created_at"]


class RoomJoinSerializer(serializers.Serializer):
    room_id = serializers.UUIDField(required=False)
    join_code = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        room_id = attrs.get("room_id")
        join_code = (attrs.get("join_code") or "").strip()
        if not room_id and not join_code:
            raise serializers.ValidationError("room_id or join_code is required")
        attrs["join_code"] = join_code
        return attrs
