import json
from channels.generic.websocket import AsyncWebsocketConsumer


class RoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.group = f"room_{self.room_id}"
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

        # Presence signal (optional)
        await self.channel_layer.group_send(self.group, {
            "type": "room.event",
            "payload": {"type": "presence", "event": "join"},
            "sender": self.channel_name,
        })

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group, self.channel_name)
        await self.channel_layer.group_send(self.group, {
            "type": "room.event",
            "payload": {"type": "presence", "event": "leave"},
            "sender": self.channel_name,
        })

    async def receive(self, text_data):
        msg = json.loads(text_data)

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
