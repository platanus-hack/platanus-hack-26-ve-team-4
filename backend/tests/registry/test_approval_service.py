from collections.abc import Callable

import pytest

from agent_zero.registry.approval_service import ApprovalService
from agent_zero.registry.errors import InvalidTransitionError, VersionNotFoundError
from agent_zero.registry.models import VersionStatus
from agent_zero.registry.publication_service import PublicationService
from agent_zero.registry.schemas import AgentManifest
from agent_zero.shared.database import Database
from tests.registry.conftest import FakeClock


@pytest.mark.requirement("REG-03")
async def test_approve_then_deprecate_records_actor_and_times(
    database: Database, make_manifest: Callable[..., AgentManifest], clock: FakeClock
) -> None:
    async with database.sessions() as db:
        await PublicationService(db, clock=clock).publish(make_manifest())
        service = ApprovalService(db, clock=clock)
        approved = await service.approve("agente-finanzas", "1.0.0", "ana")
        clock.advance(60)
        deprecated = await service.deprecate("agente-finanzas", "1.0.0")
    assert approved.status is VersionStatus.APPROVED
    assert approved.approved_by == "ana"
    assert approved.approved_at is not None
    assert deprecated.status is VersionStatus.DEPRECATED
    assert deprecated.deprecated_at == clock.now


@pytest.mark.requirement("REG-03")
async def test_invalid_transitions_and_missing_versions_fail(
    database: Database, make_manifest: Callable[..., AgentManifest]
) -> None:
    async with database.sessions() as db:
        await PublicationService(db).publish(make_manifest())
        service = ApprovalService(db)
        with pytest.raises(InvalidTransitionError):
            await service.deprecate("agente-finanzas", "1.0.0")
        await service.approve("agente-finanzas", "1.0.0", "ana")
        with pytest.raises(InvalidTransitionError):
            await service.approve("agente-finanzas", "1.0.0", "ana")
        with pytest.raises(VersionNotFoundError):
            await service.approve("nada", "1.0.0", "ana")
