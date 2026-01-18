import uuid
from django.db import models


class Room(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    # MVP: lightweight "join token"
    join_code = models.CharField(max_length=32, blank=True, default="")
    janus_room_id = models.BigIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.id} {self.title}"
