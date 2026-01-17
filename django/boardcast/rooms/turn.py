import base64
import hmac
import time
from hashlib import sha1
from django.conf import settings


def generate_turn_credentials(identity: str, ttl_seconds: int = 3600):
    expiry = int(time.time()) + ttl_seconds
    username = f"{expiry}:{identity}"

    secret = settings.TURN_STATIC_AUTH_SECRET.encode("utf-8")
    digest = hmac.new(secret, username.encode("utf-8"), sha1).digest()
    password = base64.b64encode(digest).decode("utf-8")
    return username, password
