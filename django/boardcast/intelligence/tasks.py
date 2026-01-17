from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from media_ingest.models import AudioChunk


@shared_task
def process_audio_chunk_async(chunk_id: str):
    """
    MVP stub:
    - "Transcribe" (placeholder)
    - "Detect importance" (placeholder)
    - Push to room WS group
    """
    chunk = AudioChunk.objects.get(id=chunk_id)

    # TODO: real transcription here
    transcript_text = f"[stub] Received audio chunk {chunk_id}"

    # TODO: real importance detection here
    is_important = True

    channel_layer = get_channel_layer()
    group = f"room_{chunk.room_id}"

    # Live transcript push
    async_to_sync(channel_layer.group_send)(group, {
        "type": "room.event",
        "payload": {"type": "transcript", "text": transcript_text},
        "sender": None,
    })

    # Highlight push
    if is_important:
        async_to_sync(channel_layer.group_send)(group, {
            "type": "room.event",
            "payload": {
                "type": "highlight",
                "title": "Key moment (stub)",
                "detail": transcript_text,
            },
            "sender": None,
        })
