from django.urls import path

from .views import (
    DigitizationFrameUploadView,
    DigitizationJobCreateView,
    DigitizationJobDetailView,
    DigitizationJobRunView,
    LatestWhiteboardView,
)

urlpatterns = [
    path("rooms/<uuid:room_id>/digitization-jobs/", DigitizationJobCreateView.as_view()),
    path("digitization-jobs/<uuid:job_id>/frames/", DigitizationFrameUploadView.as_view()),
    path("digitization-jobs/<uuid:job_id>/run/", DigitizationJobRunView.as_view()),
    path("digitization-jobs/<uuid:job_id>/", DigitizationJobDetailView.as_view()),
    path("rooms/<uuid:room_id>/whiteboard/latest/", LatestWhiteboardView.as_view()),
]
