from django.urls import path
from .views import AudioChunkUploadView

urlpatterns = [
    path("audio-chunks/", AudioChunkUploadView.as_view()),
]
