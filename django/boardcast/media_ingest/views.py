from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import AudioChunkUploadSerializer
from intelligence.tasks import process_audio_chunk_async


class AudioChunkUploadView(APIView):
    def post(self, request):
        s = AudioChunkUploadSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        chunk = s.save()

        # Trigger async processing (transcribe + importance)
        process_audio_chunk_async.delay(str(chunk.id))

        return Response({"id": str(chunk.id)}, status=status.HTTP_201_CREATED)
