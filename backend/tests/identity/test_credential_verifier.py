import pytest

from agent_zero.config import Settings
from agent_zero.identity.credential_issuer import CredentialIssuer
from agent_zero.identity.credential_verifier import CredentialVerifier
from agent_zero.identity.errors import IdentityDeniedError
from agent_zero.identity.models import IdentityDenialReason
from agent_zero.identity.revocation_service import RevocationService
from agent_zero.identity.schemas import AgentGrant
from agent_zero.shared.database import Database
from tests.identity.conftest import FakeClock


async def _denial(verifier: CredentialVerifier, token: str, scope: str) -> IdentityDenialReason:
    with pytest.raises(IdentityDeniedError) as error:
        await verifier.verify(token, scope)
    return error.value.reason


@pytest.mark.requirement("IDN-01", "IDN-02")
async def test_valid_credential_is_accepted(
    database: Database, identity_settings: Settings, clock: FakeClock, grant: AgentGrant
) -> None:
    issued = CredentialIssuer(identity_settings, clock).issue(grant)
    async with database.sessions() as db:
        verifier = CredentialVerifier(identity_settings, RevocationService(db, clock), clock)
        assert await verifier.verify(issued.token, "tool:get_order") == issued.principal


@pytest.mark.requirement("IDN-02")
async def test_each_failure_has_its_own_reason(
    database: Database, identity_settings: Settings, clock: FakeClock, grant: AgentGrant
) -> None:
    token = CredentialIssuer(identity_settings, clock).issue(grant).token
    payload, signature = token.split(".")
    tampered = ("B" if payload[0] != "B" else "C") + payload[1:] + "." + signature
    async with database.sessions() as db:
        verifier = CredentialVerifier(identity_settings, RevocationService(db, clock), clock)
        assert await _denial(verifier, "basura", "tool:get_order") is IdentityDenialReason.MALFORMED
        assert (
            await _denial(verifier, tampered, "tool:get_order")
            is IdentityDenialReason.BAD_SIGNATURE
        )
        assert (
            await _denial(verifier, token, "tool:refund_order")
            is IdentityDenialReason.MISSING_SCOPE
        )
        clock.advance(900)
        assert await _denial(verifier, token, "tool:get_order") is IdentityDenialReason.EXPIRED


@pytest.mark.requirement("IDN-02")
@pytest.mark.parametrize("scope", ["", "tool", "*", "tool:", "TOOL:get_order"])
async def test_empty_or_unknown_scope_is_denied(
    database: Database, identity_settings: Settings, clock: FakeClock, grant: AgentGrant, scope: str
) -> None:
    token = CredentialIssuer(identity_settings, clock).issue(grant).token
    async with database.sessions() as db:
        verifier = CredentialVerifier(identity_settings, RevocationService(db, clock), clock)
        assert await _denial(verifier, token, scope) is IdentityDenialReason.MISSING_SCOPE


@pytest.mark.requirement("IDN-02")
async def test_credential_without_scopes_is_denied(
    database: Database, identity_settings: Settings, clock: FakeClock, grant: AgentGrant
) -> None:
    token = (
        CredentialIssuer(identity_settings, clock)
        .issue(grant.model_copy(update={"scopes": ()}))
        .token
    )
    async with database.sessions() as db:
        verifier = CredentialVerifier(identity_settings, RevocationService(db, clock), clock)
        assert await _denial(verifier, token, "memory:read") is IdentityDenialReason.MISSING_SCOPE


@pytest.mark.requirement("IDN-03")
async def test_revoked_credential_fails_with_valid_signature_and_expiry(
    database: Database, identity_settings: Settings, clock: FakeClock, grant: AgentGrant
) -> None:
    issued = CredentialIssuer(identity_settings, clock).issue(grant)
    async with database.sessions() as db:
        revocations = RevocationService(db, clock)
        verifier = CredentialVerifier(identity_settings, revocations, clock)
        await verifier.verify(issued.token, "memory:read")
        await revocations.revoke_credential(issued.principal.credential_id)
        assert await _denial(verifier, issued.token, "memory:read") is IdentityDenialReason.REVOKED


@pytest.mark.requirement("IDN-03")
async def test_revoked_agent_fails_all_its_credentials(
    database: Database, identity_settings: Settings, clock: FakeClock, grant: AgentGrant
) -> None:
    issuer = CredentialIssuer(identity_settings, clock)
    first, second = issuer.issue(grant), issuer.issue(grant)
    async with database.sessions() as db:
        revocations = RevocationService(db, clock)
        verifier = CredentialVerifier(identity_settings, revocations, clock)
        await revocations.revoke_agent("agent-soporte")
        assert await _denial(verifier, first.token, "memory:read") is IdentityDenialReason.REVOKED
        assert await _denial(verifier, second.token, "memory:read") is IdentityDenialReason.REVOKED
