import uuid
from django.db import models


class AudioChunk(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to="audio_chunks/")
    duration_ms = models.IntegerField(default=0)
