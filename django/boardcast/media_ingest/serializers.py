from rest_framework import serializers
from .models import AudioChunk


class AudioChunkUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioChunk
        fields = ["id", "room_id", "file", "duration_ms", "created_at"]
        read_only_fields = ["id", "created_at"]
