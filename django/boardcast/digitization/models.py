import uuid
from pathlib import Path

from django.db import models

from rooms.models import Room
from .constants import STATUS_CHOICES, STATUS_CREATED


def frame_upload_to(instance, filename):
    ext = Path(filename).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        ext = ".jpg"
    return f"digitization/{instance.job_id}/frames/frame_{instance.frame_index}{ext}"


def job_result_upload_to(instance, filename):
    return f"digitization/{instance.id}/{filename}"


class DigitizationJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="digitization_jobs")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CREATED)
    stage = models.CharField(max_length=64, blank=True, default="")
    expected_frames = models.IntegerField(default=9)
    frame_width = models.IntegerField(null=True, blank=True)
    frame_height = models.IntegerField(null=True, blank=True)
    capture_source = models.CharField(max_length=64, blank=True, default="")
    options = models.JSONField(default=dict, blank=True)
    metrics = models.JSONField(default=dict, blank=True)

    processed_frames = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    error_code = models.CharField(max_length=64, blank=True, default="")
    error_message = models.TextField(blank=True, default="")

    result_image = models.FileField(upload_to=job_result_upload_to, null=True, blank=True)
    background_image = models.FileField(upload_to=job_result_upload_to, null=True, blank=True)
    debug_image = models.FileField(upload_to=job_result_upload_to, null=True, blank=True)

    def __str__(self):
        return f"{self.id} {self.room_id} {self.status}"


class DigitizationFrame(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(DigitizationJob, on_delete=models.CASCADE, related_name="frames")
    frame_index = models.IntegerField()
    captured_at = models.DateTimeField(null=True, blank=True)
    image = models.FileField(upload_to=frame_upload_to)
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    checksum = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["job", "frame_index"], name="uniq_digitization_frame_index"),
        ]
        ordering = ["frame_index"]

    def __str__(self):
        return f"{self.id} {self.job_id} idx={self.frame_index}"
