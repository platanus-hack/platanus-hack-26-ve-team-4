import base64
import json
from datetime import UTC, datetime, timedelta

import pytest

from agent_zero.sessions.session_token import SessionTokenCodec, SessionTokenError

KEY = b"clave-de-sesion-de-prueba"
TTL = timedelta(hours=4)


class FakeClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


def _payload(token: str) -> dict[str, object]:
    part = token.split(".", maxsplit=1)[0]
    decoded: dict[str, object] = json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
    return decoded


def test_token_round_trips_the_session_id() -> None:
    codec = SessionTokenCodec(KEY, TTL, FakeClock())

    issued = codec.issue("sess-abc")

    assert codec.verify(issued.token) == "sess-abc"
    assert issued.expires_at == datetime(2026, 10, 24, 16, 0, tzinfo=UTC)


def test_token_carries_no_customer_identity_or_route() -> None:
    issued = SessionTokenCodec(KEY, TTL, FakeClock()).issue("sess-abc")

    assert set(_payload(issued.token)) == {"sid", "exp"}


def test_expired_token_is_rejected() -> None:
    clock = FakeClock()
    codec = SessionTokenCodec(KEY, TTL, clock)
    token = codec.issue("sess-abc").token

    clock.now += TTL
    with pytest.raises(SessionTokenError):
        codec.verify(token)


def test_token_signed_with_another_key_is_rejected() -> None:
    token = SessionTokenCodec(b"otra-clave", TTL, FakeClock()).issue("sess-abc").token

    with pytest.raises(SessionTokenError):
        SessionTokenCodec(KEY, TTL, FakeClock()).verify(token)


def test_payload_swapped_under_a_valid_signature_is_rejected() -> None:
    codec = SessionTokenCodec(KEY, TTL, FakeClock())
    victim = codec.issue("sess-victima").token
    attacker = codec.issue("sess-atacante").token

    forged = f"{victim.split('.')[0]}.{attacker.split('.')[1]}"
    with pytest.raises(SessionTokenError):
        codec.verify(forged)


@pytest.mark.parametrize("token", ["", "a", "a.b.c", "abc.%%%", "e30.e30"])
def test_malformed_tokens_are_rejected(token: str) -> None:
    with pytest.raises(SessionTokenError):
        SessionTokenCodec(KEY, TTL, FakeClock()).verify(token)
