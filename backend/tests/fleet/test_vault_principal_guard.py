import pytest

from agent_zero.config import Settings
from agent_zero.fleet.fleet_builder import Fleet, build_fleet
from agent_zero.identity.errors import IdentityDeniedError
from agent_zero.identity.models import IdentityDenialReason
from agent_zero.identity.revocation_service import RevocationService
from agent_zero.identity.schemas import AgentPrincipal
from agent_zero.memory_bank.memory_forget_service import MemoryForgetService
from agent_zero.memory_bank.memory_read_service import MemoryReadService
from agent_zero.memory_bank.memory_write_service import MemoryWriteService
from agent_zero.shared.database import Database
from tests.agent_gateway.support import build_manifest
from tests.fleet.support import publish_approved
from tests.identity.conftest import FakeClock
from tests.memory_bank.conftest import make_request

SCOPES = ("memory:read", "memory:write")


async def admitted(fleet: Fleet) -> AgentPrincipal:
    await publish_approved(fleet, build_manifest(scopes=SCOPES))
    return await fleet.admission.admit("agente-soporte", "1.0.0")


async def write_memory(fleet: Fleet, principal: AgentPrincipal) -> None:
    async with fleet.database.sessions() as db:
        writer = MemoryWriteService(
            db, fleet.settings, fleet.cipher, fleet.memory_guard, clock=fleet.clock
        )
        await writer.write(principal, make_request("saldo del cliente 5000 USD"))


async def recall(fleet: Fleet, principal: AgentPrincipal) -> list[str]:
    async with fleet.database.sessions() as db:
        reader = MemoryReadService(db, fleet.cipher, fleet.memory_guard, fleet.clock)
        return [item.content for item in await reader.recall(principal, "cliente-1")]


@pytest.mark.requirement("MEM-02", "MEM-01")
async def test_genuine_principal_reads_and_writes(
    fleet_settings: Settings, database: Database, clock: FakeClock
) -> None:
    fleet = build_fleet(fleet_settings, database, clock)
    principal = await admitted(fleet)
    await write_memory(fleet, principal)
    assert await recall(fleet, principal) == ["saldo del cliente 5000 USD"]
    await fleet.stop()


@pytest.mark.requirement("MEM-02")
async def test_forged_principal_copy_cannot_read_write_or_forget(
    fleet_settings: Settings, database: Database, clock: FakeClock
) -> None:
    fleet = build_fleet(fleet_settings, database, clock)
    principal = await admitted(fleet)
    await write_memory(fleet, principal)
    forged = principal.model_copy(update={"agent_id": "agente-victima"})
    swapped = principal.model_copy(update={"credential_id": "x"})
    escalated = principal.model_copy(update={"scopes": ("memory:read", "memory:write", "a:b")})
    for impostor in (forged, swapped, escalated):
        with pytest.raises(IdentityDeniedError):
            await recall(fleet, impostor)
        with pytest.raises(IdentityDeniedError):
            await write_memory(fleet, impostor)
        async with fleet.database.sessions() as db:
            guard = fleet.memory_guard
            with pytest.raises(IdentityDeniedError):
                await MemoryForgetService(db, guard).forget_subject(impostor, "cliente-1")
    assert await recall(fleet, principal) == ["saldo del cliente 5000 USD"]
    await fleet.stop()


@pytest.mark.requirement("MEM-02", "IDN-03")
async def test_revoked_agent_loses_memory_access_immediately(
    fleet_settings: Settings, database: Database, clock: FakeClock
) -> None:
    fleet = build_fleet(fleet_settings, database, clock)
    principal = await admitted(fleet)
    await write_memory(fleet, principal)
    async with database.sessions() as db:
        await RevocationService(db, clock).revoke_agent("agente-soporte", "1.0.0")
    with pytest.raises(IdentityDeniedError) as caught:
        await recall(fleet, principal)
    assert caught.value.reason is IdentityDenialReason.REVOKED
    await fleet.stop()


@pytest.mark.requirement("MEM-02", "IDN-02")
async def test_expired_credential_loses_memory_access(
    fleet_settings: Settings, database: Database, clock: FakeClock
) -> None:
    fleet = build_fleet(fleet_settings, database, clock)
    principal = await admitted(fleet)
    clock.advance(seconds=fleet_settings.identity_token_ttl_seconds + 1)
    with pytest.raises(IdentityDeniedError):
        await recall(fleet, principal)
    await fleet.stop()


@pytest.mark.requirement("MEM-02")
async def test_principal_without_a_vaulted_credential_is_refused(
    fleet_settings: Settings, database: Database, clock: FakeClock
) -> None:
    fleet = build_fleet(fleet_settings, database, clock)
    principal = await admitted(fleet)
    other = build_fleet(fleet_settings, database, clock)
    with pytest.raises(IdentityDeniedError) as caught:
        await other.memory_guard.authorize(principal, "memory:read")
    assert caught.value.reason is IdentityDenialReason.MALFORMED
    await fleet.stop()
    await other.stop()
