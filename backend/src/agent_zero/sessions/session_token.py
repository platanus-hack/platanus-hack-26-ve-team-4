import base64
import binascii
import hashlib
import hmac
import json
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel

from agent_zero.shared.clock import utc_now

_B64URL = re.compile(r"^[A-Za-z0-9_-]+$")


class SessionTokenError(Exception):
    pass


class IssuedSessionToken(BaseModel):
    token: str
    expires_at: datetime


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(text: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    except (binascii.Error, ValueError) as error:
        raise SessionTokenError from error


class SessionTokenCodec:
    """Firma `session_id` y vencimiento; nunca lleva `customer_id` ni la ruta."""

    def __init__(
        self, signing_key: bytes, ttl: timedelta, clock: Callable[[], datetime] = utc_now
    ) -> None:
        self._key = signing_key
        self._ttl = ttl
        self._clock = clock

    def _sign(self, payload_part: str) -> bytes:
        return hmac.new(self._key, payload_part.encode("ascii"), hashlib.sha256).digest()

    def issue(self, session_id: str) -> IssuedSessionToken:
        expires_at = (self._clock() + self._ttl).replace(microsecond=0)
        payload = {"sid": session_id, "exp": int(expires_at.timestamp())}
        payload_part = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        token = f"{payload_part}.{_b64encode(self._sign(payload_part))}"
        return IssuedSessionToken(token=token, expires_at=expires_at)

    def verify(self, token: str) -> str:
        parts = token.split(".")
        if len(parts) != 2 or not all(_B64URL.fullmatch(part) for part in parts):
            raise SessionTokenError
        payload_part, signature_part = parts
        if not hmac.compare_digest(_b64decode(signature_part), self._sign(payload_part)):
            raise SessionTokenError
        try:
            payload = json.loads(_b64decode(payload_part))
            session_id, expires = payload["sid"], payload["exp"]
        except (ValueError, TypeError, KeyError) as error:
            raise SessionTokenError from error
        if not isinstance(session_id, str) or not isinstance(expires, int):
            raise SessionTokenError
        if datetime.fromtimestamp(expires, UTC) <= self._clock():
            raise SessionTokenError
        return session_id
