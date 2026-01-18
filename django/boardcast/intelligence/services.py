import json
import logging
import re
from typing import Dict, Optional

import redis
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_KEYWORD_REGEX = re.compile(
    r"\b(quiz|exam|midterm|final|test|assignment|homework|deadline|due|graded|important|remember)\b",
    re.IGNORECASE,
)
_PHRASES = [
    "this will be on",
    "will be on the quiz",
    "will be on the exam",
    "next week",
]

_redis_client = None


def _get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def transcribe_audio_chunk(chunk) -> str:
    if not settings.ELEVENLABS_API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY is not set")

    with chunk.file.open("rb") as handle:
        content_type = getattr(handle, "content_type", None)
        if not content_type:
            content_type = getattr(chunk.file, "content_type", None)
        if not content_type:
            content_type = "application/octet-stream"

        files = {
            settings.ELEVENLABS_STT_FILE_FIELD: (
                chunk.file.name,
                handle,
                content_type,
            )
        }
        data = {"model_id": settings.ELEVENLABS_STT_MODEL_ID}
        if settings.ELEVENLABS_STT_LANGUAGE_CODE:
            data["language_code"] = settings.ELEVENLABS_STT_LANGUAGE_CODE
        if settings.ELEVENLABS_STT_DIARIZE:
            data["diarize"] = "true"

        resp = requests.post(
            settings.ELEVENLABS_STT_URL,
            headers={"xi-api-key": settings.ELEVENLABS_API_KEY},
            data=data,
            files=files,
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()

    transcript_text = payload.get("text") or payload.get("transcription") or ""
    return transcript_text.strip()


def update_transcript_context(room_id: str, transcript: str) -> str:
    if not transcript:
        return ""

    try:
        client = _get_redis_client()
        key = f"room:{room_id}:transcripts"
        max_chunks = settings.TRANSCRIPT_CONTEXT_MAX_CHUNKS

        pipe = client.pipeline()
        pipe.rpush(key, transcript)
        pipe.ltrim(key, -max_chunks, -1)
        pipe.lrange(key, 0, -1)
        context_parts = pipe.execute()[-1]

        return "\n".join(context_parts)
    except Exception:
        logger.exception("Failed to update transcript context for room %s", room_id)
        return transcript


def detect_highlight(transcript: str, context: str) -> Optional[Dict[str, str]]:
    if not transcript:
        return None
    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY is not set; skipping highlight detection")
        return None
    if not _should_consider_highlight(transcript):
        return None

    prompt = _build_prompt(transcript, context)
    url = f"{settings.GEMINI_BASE_URL}/models/{settings.GEMINI_MODEL}:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 256},
    }

    try:
        resp = requests.post(
            url,
            params={"key": settings.GEMINI_API_KEY},
            json=payload,
            timeout=20,
        )
        resp.raise_for_status()
    except requests.RequestException:
        logger.exception("Gemini request failed")
        return None

    response_text = _extract_candidate_text(resp.json())
    if not response_text:
        return None

    data = _safe_parse_json(response_text)
    if not data:
        return None

    important = data.get("important")
    if isinstance(important, str):
        important = important.strip().lower() == "true"
    if not important:
        return None

    try:
        confidence = float(data.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0
    if confidence and confidence < settings.GEMINI_MIN_CONFIDENCE:
        return None

    title = (data.get("title") or "Key moment").strip()
    detail = (data.get("detail") or transcript).strip()
    if not title or not detail:
        return None

    return {"title": title, "detail": detail}


def _should_consider_highlight(transcript: str) -> bool:
    lowered = transcript.lower()
    if any(phrase in lowered for phrase in _PHRASES):
        return True
    return bool(_KEYWORD_REGEX.search(transcript))


def _build_prompt(transcript: str, context: str) -> str:
    context_block = context.strip()
    if context_block:
        context_block = f"Recent context (oldest to newest):\n{context_block}\n\n"

    return (
        "You are a teaching assistant. Identify whether the latest transcript includes an "
        "important student-facing trigger (quiz, exam, assignment, deadline, important note). "
        "Return JSON only with keys: important (bool), title (string), detail (string), confidence (0-1).\n\n"
        f"{context_block}"
        f"Latest transcript:\n{transcript}\n"
    )


def _extract_candidate_text(payload: Dict) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(part.get("text", "") for part in parts).strip()


def _safe_parse_json(text: str) -> Optional[Dict]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Failed to parse Gemini JSON response: %s", text)
        return None
