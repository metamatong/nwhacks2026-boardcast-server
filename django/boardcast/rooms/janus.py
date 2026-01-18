import json
import secrets
import time
import uuid
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


class JanusError(Exception):
    pass


class JanusClient:
    def __init__(self, base_url: str, api_secret: str, admin_key: str, timeout_seconds: int):
        if not base_url:
            raise JanusError("Janus URL not configured")
        self.base_url = base_url.rstrip("/")
        self.api_secret = api_secret
        self.admin_key = admin_key
        self.timeout_seconds = timeout_seconds

    def create_videoroom(self, description: str) -> int:
        session_id = None
        try:
            session_id = self._create_session()
            handle_id = self._attach_plugin(session_id)
            return self._create_room(session_id, handle_id, description)
        finally:
            if session_id:
                self._destroy_session(session_id)

    def _create_session(self) -> int:
        resp = self._post(
            self.base_url,
            {
                "janus": "create",
                "transaction": self._transaction(),
            },
        )
        if resp.get("janus") != "success" or "data" not in resp:
            raise JanusError(f"Unexpected response creating session: {resp}")
        return int(resp["data"]["id"])

    def _attach_plugin(self, session_id: int) -> int:
        resp = self._post(
            f"{self.base_url}/{session_id}",
            {
                "janus": "attach",
                "plugin": "janus.plugin.videoroom",
                "transaction": self._transaction(),
            },
        )
        if resp.get("janus") != "success" or "data" not in resp:
            raise JanusError(f"Unexpected response attaching plugin: {resp}")
        return int(resp["data"]["id"])

    def _create_room(self, session_id: int, handle_id: int, description: str) -> int:
        room_id = self._generate_room_id()
        body = {
            "request": "create",
            "permanent": False,
            "description": description,
            "room": room_id,
        }
        if self.admin_key:
            body["admin_key"] = self.admin_key

        resp = self._post(
            f"{self.base_url}/{session_id}/{handle_id}",
            {
                "janus": "message",
                "transaction": self._transaction(),
                "body": body,
            },
        )

        if resp.get("janus") == "ack":
            resp = self._poll_event(session_id, handle_id)

        room = self._extract_room_id(resp)
        if not room:
            raise JanusError(f"Room creation failed: {resp}")
        return int(room)

    def _poll_event(self, session_id: int, handle_id: int, attempts: int = 5):
        for _ in range(attempts):
            rid = int(time.time() * 1000)
            params = urlencode({"rid": rid, "maxev": 1})
            resp = self._get(f"{self.base_url}/{session_id}/{handle_id}?{params}")
            if resp.get("janus") == "event":
                return resp
            if resp.get("janus") == "error":
                raise JanusError(f"Janus error: {resp}")
            time.sleep(0.2)
        raise JanusError("Timed out waiting for Janus event")

    def _extract_room_id(self, resp) -> int | None:
        if resp.get("janus") == "error":
            raise JanusError(resp.get("error", {}).get("reason", "Janus error"))
        plugindata = resp.get("plugindata", {}).get("data", {})
        if plugindata.get("videoroom") == "created":
            return plugindata.get("room")
        if plugindata.get("error"):
            raise JanusError(plugindata.get("error"))
        return plugindata.get("room")

    def _destroy_session(self, session_id: int) -> None:
        try:
            self._post(
                f"{self.base_url}/{session_id}",
                {
                    "janus": "destroy",
                    "transaction": self._transaction(),
                },
            )
        except JanusError:
            pass

    def _generate_room_id(self) -> int:
        return secrets.randbelow(900_000_000) + 100_000_000

    def _transaction(self) -> str:
        return uuid.uuid4().hex

    def _post(self, url: str, payload: dict) -> dict:
        req_payload = dict(payload)
        if self.api_secret:
            req_payload["apisecret"] = self.api_secret
        data = json.dumps(req_payload).encode("utf-8")
        req = Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=self.timeout_seconds) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise JanusError(str(exc)) from exc

    def _get(self, url: str) -> dict:
        try:
            with urlopen(url, timeout=self.timeout_seconds) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise JanusError(str(exc)) from exc


def create_videoroom(description: str) -> int:
    client = JanusClient(
        base_url=settings.JANUS_URL,
        api_secret=settings.JANUS_API_SECRET,
        admin_key=settings.JANUS_ADMIN_KEY,
        timeout_seconds=settings.JANUS_TIMEOUT_SECONDS,
    )
    return client.create_videoroom(description=description)
