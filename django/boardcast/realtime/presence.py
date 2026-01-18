import json
import uuid
from datetime import datetime, timezone

import redis
from django.conf import settings

ROOM_PARTICIPANTS_TTL_SECONDS = 6 * 60 * 60
DEFAULT_DISPLAY_NAME = "Guest"


def _client() -> redis.Redis:
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def _room_key(room_id: str) -> str:
    return f"room:{room_id}:participants"


def build_participant(name: str | None, role: str, client_id: str | None = None) -> dict:
    participant_id = client_id or uuid.uuid4().hex
    display_name = (name or "").strip() or DEFAULT_DISPLAY_NAME
    return {
        "id": participant_id,
        "name": display_name,
        "role": role,
        "joined_at": datetime.now(timezone.utc).isoformat(),
    }


def upsert_participant(room_id: str, participant: dict) -> list[dict]:
    key = _room_key(room_id)
    client = _client()
    client.hset(key, participant["id"], json.dumps(participant))
    client.expire(key, ROOM_PARTICIPANTS_TTL_SECONDS)
    return list_participants(room_id, client=client)


def remove_participant(room_id: str, participant_id: str) -> list[dict]:
    key = _room_key(room_id)
    client = _client()
    client.hdel(key, participant_id)
    participants = list_participants(room_id, client=client)
    if not participants:
        client.delete(key)
    return participants


def list_participants(room_id: str, client: redis.Redis | None = None) -> list[dict]:
    key = _room_key(room_id)
    client = client or _client()
    raw_entries = client.hgetall(key)
    participants: list[dict] = []
    for raw in raw_entries.values():
        try:
            participants.append(json.loads(raw))
        except (TypeError, json.JSONDecodeError):
            continue
    participants.sort(key=lambda item: item.get("joined_at", ""))
    return participants
