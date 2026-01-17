from rest_framework import serializers
from .models import Room


class RoomCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["id", "title", "join_code", "created_at"]
        read_only_fields = ["id", "created_at"]


class RoomJoinSerializer(serializers.Serializer):
    room_id = serializers.UUIDField()
    join_code = serializers.CharField(required=False, allow_blank=True)
