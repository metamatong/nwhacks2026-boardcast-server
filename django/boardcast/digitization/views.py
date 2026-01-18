from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from rooms.models import Room
from .constants import (
    STATUS_CREATED,
    STATUS_FAILED,
    STATUS_QUEUED,
    STATUS_RUNNING,
    STATUS_SUCCEEDED,
    STATUS_UPLOADING,
    STAGE_LOADING,
)
from .models import DigitizationFrame, DigitizationJob
from .serializers import DigitizationFrameUploadSerializer, DigitizationJobCreateSerializer
from .tasks import process_digitization_job


def _file_url(request, file_field):
    if not file_field:
        return None
    return request.build_absolute_uri(file_field.url)


class DigitizationJobCreateView(APIView):
    def post(self, request, room_id):
        room = get_object_or_404(Room, id=room_id)
        s = DigitizationJobCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        expected_frames = s.validated_data.get(
            "expected_frames",
            getattr(settings, "DIGITIZATION_DEFAULT_EXPECTED_FRAMES", 9),
        )

        job = DigitizationJob.objects.create(
            room=room,
            expected_frames=expected_frames,
            frame_width=s.validated_data.get("frame_width"),
            frame_height=s.validated_data.get("frame_height"),
            capture_source=s.validated_data.get("capture_source", ""),
            options=s.validated_data.get("options") or {},
            status=STATUS_CREATED,
        )

        return Response(
            {
                "job_id": str(job.id),
                "status": job.status,
                "upload": {
                    "mode": "multipart",
                    "frame_upload_url": f"/api/digitization-jobs/{job.id}/frames/",
                },
            },
            status=status.HTTP_201_CREATED,
        )


class DigitizationFrameUploadView(APIView):
    def post(self, request, job_id):
        import cv2
        import numpy as np

        job = get_object_or_404(DigitizationJob, id=job_id)
        if job.status not in {STATUS_CREATED, STATUS_UPLOADING, STATUS_FAILED}:
            return Response(
                {"detail": "Job is not accepting uploads"},
                status=status.HTTP_409_CONFLICT,
            )

        s = DigitizationFrameUploadSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        frame_index = s.validated_data["frame_index"]
        if frame_index < 0:
            return Response({"detail": "frame_index must be >= 0"}, status=status.HTTP_400_BAD_REQUEST)
        if job.expected_frames and frame_index >= job.expected_frames:
            return Response({"detail": "frame_index exceeds expected_frames"}, status=status.HTTP_400_BAD_REQUEST)

        image = s.validated_data["image"]
        data = image.read()
        image.seek(0)
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return Response({"detail": "Invalid image payload"}, status=status.HTTP_400_BAD_REQUEST)
        height, width = img.shape[:2]

        captured_at = s.validated_data.get("captured_at")

        frame, created = DigitizationFrame.objects.get_or_create(
            job=job,
            frame_index=frame_index,
        )
        if not created and frame.image:
            frame.image.delete(save=False)

        frame.image = image
        frame.captured_at = captured_at
        frame.width = width
        frame.height = height
        frame.save()

        if not job.frame_width or not job.frame_height:
            job.frame_width = width
            job.frame_height = height

        if job.status in {STATUS_CREATED, STATUS_FAILED}:
            job.status = STATUS_UPLOADING
            job.error_message = ""
            job.error_code = ""
            job.save(update_fields=["status", "frame_width", "frame_height", "error_message", "error_code"])
        else:
            job.save(update_fields=["frame_width", "frame_height"])

        if getattr(settings, "DIGITIZATION_AUTO_TRIGGER", False):
            if job.frames.count() >= job.expected_frames and job.status != STATUS_QUEUED:
                job.status = STATUS_QUEUED
                job.stage = STAGE_LOADING
                job.save(update_fields=["status", "stage"])
                process_digitization_job.delay(str(job.id))

        return Response(
            {
                "frame_id": str(frame.id),
                "frame_index": frame.frame_index,
                "status": "UPLOADED",
            },
            status=status.HTTP_201_CREATED,
        )


class DigitizationJobRunView(APIView):
    def post(self, request, job_id):
        job = get_object_or_404(DigitizationJob, id=job_id)
        if job.status in {STATUS_RUNNING, STATUS_QUEUED}:
            return Response({"detail": "Job already running"}, status=status.HTTP_409_CONFLICT)
        if job.status == STATUS_SUCCEEDED:
            return Response({"detail": "Job already completed"}, status=status.HTTP_409_CONFLICT)

        frame_count = job.frames.count()
        if frame_count < job.expected_frames:
            return Response(
                {
                    "detail": "Not enough frames uploaded",
                    "uploaded_frames": frame_count,
                    "expected_frames": job.expected_frames,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        job.status = STATUS_QUEUED
        job.stage = STAGE_LOADING
        job.save(update_fields=["status", "stage"])

        process_digitization_job.delay(str(job.id))

        return Response({"job_id": str(job.id), "status": job.status}, status=status.HTTP_200_OK)


class DigitizationJobDetailView(APIView):
    def get(self, request, job_id):
        job = get_object_or_404(DigitizationJob, id=job_id)

        result = None
        if job.result_image:
            result = {
                "image_url": _file_url(request, job.result_image),
                "background_url": _file_url(request, job.background_image),
                "debug_url": _file_url(request, job.debug_image),
            }

        error = None
        if job.status == STATUS_FAILED:
            error = {
                "code": job.error_code or None,
                "message": job.error_message or None,
            }

        return Response(
            {
                "job_id": str(job.id),
                "status": job.status,
                "progress": {
                    "stage": job.stage or None,
                    "processed_frames": job.processed_frames,
                    "expected_frames": job.expected_frames,
                },
                "result": result,
                "error": error,
                "metrics": job.metrics or None,
            }
        )


class LatestWhiteboardView(APIView):
    def get(self, request, room_id):
        room = get_object_or_404(Room, id=room_id)
        job = (
            DigitizationJob.objects.filter(room=room, status=STATUS_SUCCEEDED)
            .order_by("-finished_at", "-created_at")
            .first()
        )
        if not job or not job.result_image:
            return Response({"detail": "No digitized board available"}, status=status.HTTP_404_NOT_FOUND)

        return Response(
            {
                "room_id": str(room.id),
                "image_url": _file_url(request, job.result_image),
                "generated_at": job.finished_at or job.created_at,
                "job_id": str(job.id),
            }
        )
