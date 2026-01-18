import logging

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer

from intelligence.services import (
    detect_highlight,
    transcribe_audio_chunk,
    update_transcript_context,
)
from media_ingest.models import AudioChunk

logger = logging.getLogger(__name__)


@shared_task
def process_audio_chunk_async(chunk_id: str):
    """
    Process an uploaded audio chunk:
    - Transcribe via ElevenLabs Scribe
    - Detect highlight via Gemini (keyword-gated)
    - Push transcript + highlight to room WS group
    """
    try:
        chunk = AudioChunk.objects.get(id=chunk_id)
    except AudioChunk.DoesNotExist:
        logger.warning("AudioChunk %s not found", chunk_id)
        return

    try:
        transcript_text = transcribe_audio_chunk(chunk)
    except Exception:
        logger.exception("Transcription failed for chunk %s", chunk_id)
        return

    if not transcript_text:
        return

    channel_layer = get_channel_layer()
    group = f"room_{chunk.room_id}"

    # Live transcript push
    async_to_sync(channel_layer.group_send)(group, {
        "type": "room.event",
        "payload": {"type": "transcript", "text": transcript_text},
        "sender": None,
    })

    # Highlight push
    context = update_transcript_context(str(chunk.room_id), transcript_text)
    highlight = detect_highlight(transcript_text, context)
    if highlight:
        async_to_sync(channel_layer.group_send)(group, {
            "type": "room.event",
            "payload": {
                "type": "highlight",
                "title": highlight["title"],
                "detail": highlight["detail"],
            },
            "sender": None,
        })
    else:
        logger.info("Highlight suppressed for room %s chunk %s", chunk.room_id, chunk_id)
