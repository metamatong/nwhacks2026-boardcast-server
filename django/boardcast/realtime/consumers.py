import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

from .presence import build_participant, remove_participant, upsert_participant


class RoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.group = f"room_{self.room_id}"
        self.participant_id = None
        self.participant = None
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group, self.channel_name)
        if not self.participant_id:
            return
        participants = await sync_to_async(remove_participant)(
            self.room_id,
            self.participant_id,
        )
        await self._broadcast_presence(
            "participant-left",
            participants,
            self.participant or {"id": self.participant_id},
        )
        self.participant_id = None
        self.participant = None

    async def receive(self, text_data):
        try:
            msg = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = msg.get("type")
        if msg_type in {"create-room", "join-room"}:
            role = "host" if msg_type == "create-room" else "participant"
            participant = build_participant(
                name=msg.get("name"),
                role=role,
                client_id=msg.get("client_id"),
            )
            if self.participant_id and self.participant_id != participant["id"]:
                await sync_to_async(remove_participant)(self.room_id, self.participant_id)
            participants = await sync_to_async(upsert_participant)(
                self.room_id,
                participant,
            )
            self.participant_id = participant["id"]
            self.participant = participant
            event = "room-created" if msg_type == "create-room" else "participant-joined"
            await self._broadcast_presence(event, participants, participant)
            return

        if msg_type == "leave-room":
            if not self.participant_id:
                return
            participants = await sync_to_async(remove_participant)(
                self.room_id,
                self.participant_id,
            )
            await self._broadcast_presence(
                "participant-left",
                participants,
                self.participant or {"id": self.participant_id},
            )
            self.participant_id = None
            self.participant = None
            return

        # Basic relay: offers/answers/candidates and any other JSON messages
        await self.channel_layer.group_send(self.group, {
            "type": "room.event",
            "payload": msg,
            "sender": self.channel_name,
        })

    async def room_event(self, event):
        if event.get("sender") == self.channel_name:
            return
        await self.send(text_data=json.dumps(event["payload"]))

    async def room_presence(self, event):
        await self.send(text_data=json.dumps(event["payload"]))

    async def _broadcast_presence(self, event_type: str, participants: list[dict], participant: dict | None):
        payload = {"type": event_type, "participants": participants}
        if participant:
            payload["participant"] = participant
        await self.channel_layer.group_send(self.group, {
            "type": "room.presence",
            "payload": payload,
        })
