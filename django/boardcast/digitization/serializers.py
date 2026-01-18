from django.conf import settings
from rest_framework import serializers

from .models import DigitizationFrame, DigitizationJob


class DigitizationJobCreateSerializer(serializers.Serializer):
    expected_frames = serializers.IntegerField(required=False, min_value=1, max_value=50)
    frame_width = serializers.IntegerField(required=False, min_value=1)
    frame_height = serializers.IntegerField(required=False, min_value=1)
    capture_source = serializers.CharField(required=False, allow_blank=True)
    options = serializers.JSONField(required=False)


class DigitizationFrameUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = DigitizationFrame
        fields = ["frame_index", "captured_at", "image"]

    def validate_image(self, value):
        max_bytes = getattr(settings, "DIGITIZATION_MAX_FRAME_BYTES", 3_000_000)
        if value.size > max_bytes:
            raise serializers.ValidationError("Image exceeds max file size")

        allowed_types = set(getattr(settings, "DIGITIZATION_ALLOWED_MIME_TYPES", []))
        if allowed_types and value.content_type not in allowed_types:
            raise serializers.ValidationError("Unsupported image type")

        return value


class DigitizationJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = DigitizationJob
        fields = [
            "id",
            "room_id",
            "status",
            "stage",
            "expected_frames",
            "frame_width",
            "frame_height",
            "capture_source",
            "options",
            "processed_frames",
            "created_at",
            "started_at",
            "finished_at",
            "error_code",
            "error_message",
            "metrics",
        ]
        read_only_fields = fields
