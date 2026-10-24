import pytest

from agent_zero.config import Settings
from agent_zero.identity.credential_issuer import CredentialIssuer
from agent_zero.identity.revocation_service import RevocationService
from agent_zero.identity.schemas import AgentGrant
from agent_zero.shared.database import Database
from tests.identity.conftest import FakeClock


@pytest.mark.requirement("IDN-03")
async def test_revoke_credential_only_affects_that_credential(
    database: Database, identity_settings: Settings, clock: FakeClock, grant: AgentGrant
) -> None:
    issuer = CredentialIssuer(identity_settings, clock)
    first, second = issuer.issue(grant).principal, issuer.issue(grant).principal
    async with database.sessions() as db:
        service = RevocationService(db, clock)
        await service.revoke_credential(first.credential_id)
        await service.revoke_credential(first.credential_id)
        assert await service.is_revoked(first)
        assert not await service.is_revoked(second)


@pytest.mark.requirement("IDN-03")
async def test_revoke_agent_covers_all_versions_or_one(
    database: Database, identity_settings: Settings, clock: FakeClock, grant: AgentGrant
) -> None:
    issuer = CredentialIssuer(identity_settings, clock)
    v1 = issuer.issue(grant).principal
    v2 = issuer.issue(grant.model_copy(update={"version": "2.0.0"})).principal
    other = issuer.issue(grant.model_copy(update={"agent_id": "otro"})).principal
    async with database.sessions() as db:
        service = RevocationService(db, clock)
        await service.revoke_agent("agent-soporte", "1.0.0")
        assert await service.is_revoked(v1)
        assert not await service.is_revoked(v2)
        await service.revoke_agent("agent-soporte")
        assert await service.is_revoked(v2)
        assert not await service.is_revoked(other)


@pytest.mark.requirement("IDN-03")
async def test_revocations_persist_across_sessions(
    database: Database, identity_settings: Settings, clock: FakeClock, grant: AgentGrant
) -> None:
    principal = CredentialIssuer(identity_settings, clock).issue(grant).principal
    async with database.sessions() as db:
        await RevocationService(db, clock).revoke_credential(principal.credential_id)
    async with database.sessions() as db:
        assert await RevocationService(db, clock).is_revoked(principal)
