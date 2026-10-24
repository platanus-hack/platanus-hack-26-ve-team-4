import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime

from agent_zero.config import Settings


class InvalidSessionTokenError(ValueError):
    pass


class SessionTokens:
    def __init__(self, settings: Settings) -> None:
        self._key = hmac.digest(
            settings.identity_signing_key.get_secret_value().encode(),
            b"agent-zero/arena-session/v1",
            "sha256",
        )

    def issue(self, session_id: str, expires_at: datetime) -> str:
        body = json.dumps(
            {"session_id": session_id, "exp": int(expires_at.timestamp())}, separators=(",", ":")
        ).encode()
        encoded = base64.urlsafe_b64encode(body).decode().rstrip("=")
        signature = hmac.new(self._key, encoded.encode(), hashlib.sha256).hexdigest()
        return f"{encoded}.{signature}"

    def verify(self, token: str, now: datetime | None = None) -> str:
        try:
            if len(token) > 1024:
                raise ValueError("token demasiado largo")
            body, signature = token.split(".")
            expected = hmac.new(self._key, body.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise ValueError("firma inválida")
            payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
            session_id, expiry = payload["session_id"], payload["exp"]
            if not isinstance(session_id, str) or not isinstance(expiry, int):
                raise ValueError("campos inválidos")
            if expiry <= (now or datetime.now(UTC)).timestamp():
                raise ValueError("sesión vencida")
            return session_id
        except (ValueError, TypeError, KeyError, UnicodeError) as error:
            raise InvalidSessionTokenError("Token de sesión inválido o vencido.") from error
