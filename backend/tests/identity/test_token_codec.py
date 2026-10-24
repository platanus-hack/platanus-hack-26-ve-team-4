import pytest

from agent_zero.config import Settings
from agent_zero.identity.credential_issuer import CredentialIssuer
from agent_zero.identity.errors import IdentityDeniedError
from agent_zero.identity.models import IdentityDenialReason
from agent_zero.identity.schemas import AgentGrant
from agent_zero.identity.token_codec import TokenCodec
from tests.identity.conftest import FakeClock


def _codec(settings: Settings) -> TokenCodec:
    return TokenCodec(settings.identity_signing_key.get_secret_value().encode("utf-8"))


@pytest.mark.requirement("IDN-02")
def test_roundtrip(identity_settings: Settings, clock: FakeClock, grant: AgentGrant) -> None:
    issued = CredentialIssuer(identity_settings, clock).issue(grant)
    assert _codec(identity_settings).decode(issued.token) == issued.principal


@pytest.mark.requirement("IDN-02")
@pytest.mark.parametrize(
    "token", ["", "sin-punto", "a.b.c", ".firma", "payload.", "ñ.x", "!!!.@@@"]
)
def test_malformed_tokens(identity_settings: Settings, token: str) -> None:
    with pytest.raises(IdentityDeniedError) as error:
        _codec(identity_settings).decode(token)
    assert error.value.reason is IdentityDenialReason.MALFORMED


@pytest.mark.requirement("IDN-02")
def test_tampered_payload_fails_signature(
    identity_settings: Settings, clock: FakeClock, grant: AgentGrant
) -> None:
    token = CredentialIssuer(identity_settings, clock).issue(grant).token
    payload, signature = token.split(".")
    altered = ("B" if payload[0] != "B" else "C") + payload[1:]
    with pytest.raises(IdentityDeniedError) as error:
        _codec(identity_settings).decode(f"{altered}.{signature}")
    assert error.value.reason is IdentityDenialReason.BAD_SIGNATURE


@pytest.mark.requirement("IDN-02")
def test_other_key_fails_signature(
    identity_settings: Settings, clock: FakeClock, grant: AgentGrant
) -> None:
    token = CredentialIssuer(identity_settings, clock).issue(grant).token
    with pytest.raises(IdentityDeniedError) as error:
        TokenCodec(b"otra-clave").decode(token)
    assert error.value.reason is IdentityDenialReason.BAD_SIGNATURE
