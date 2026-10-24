import pytest

from agent_zero.config import Settings
from agent_zero.fleet.fleet_builder import build_fleet
from agent_zero.fleet.registry_admission import RegistryAdmission
from agent_zero.identity.revocation_service import RevocationService
from agent_zero.registry.approval_service import ApprovalService
from agent_zero.registry.publication_service import PublicationService
from agent_zero.runtime.admission import AdmissionDeniedError
from agent_zero.runtime.handlers import StepContext
from agent_zero.runtime.models import RunStatus
from agent_zero.runtime.step_results import Complete, StepResult
from agent_zero.shared.database import Database
from tests.agent_gateway.support import build_manifest
from tests.fleet.support import drain, enqueue_run, load_run, publish_approved
from tests.identity.conftest import FakeClock


class CountingHandler:
    name = "contador"

    def __init__(self) -> None:
        self.executed = 0

    async def step(self, context: StepContext) -> StepResult:
        self.executed += 1
        return Complete(output={"agent": context.principal.agent_id})


@pytest.mark.requirement("IDN-01", "REG-03")
async def test_admits_only_approved_versions(
    fleet_settings: Settings, database: Database, clock: FakeClock
) -> None:
    fleet = build_fleet(fleet_settings, database, clock)
    admission: RegistryAdmission = fleet.admission
    with pytest.raises(AdmissionDeniedError, match="Admisión denegada"):
        await admission.admit("agente-soporte", "1.0.0")
    await publish_approved(fleet, build_manifest())
    principal = await admission.admit("agente-soporte", "1.0.0")
    assert principal.agent_id == "agente-soporte"
    assert principal.scopes == ("tool:get_ledger", "tool:get_order", "tool:get_secret")
    await fleet.stop()


@pytest.mark.requirement("IDN-01", "REG-03")
async def test_draft_gets_no_identity(
    fleet_settings: Settings, database: Database, clock: FakeClock
) -> None:
    fleet = build_fleet(fleet_settings, database, clock)
    async with database.sessions() as db:
        await PublicationService(db, fleet.armor, clock).publish(build_manifest())
    with pytest.raises(AdmissionDeniedError) as caught:
        await fleet.admission.admit("agente-soporte", "1.0.0")
    assert "no está aprobada" in caught.value.reason
    await fleet.stop()


@pytest.mark.requirement("RUN-04")
async def test_deprecated_agent_run_fails_without_executing_steps(
    fleet_settings: Settings, database: Database, clock: FakeClock
) -> None:
    fleet = build_fleet(fleet_settings, database, clock)
    handler = CountingHandler()
    fleet.handlers.register(handler)
    await publish_approved(fleet, build_manifest())
    run_id = await enqueue_run(fleet, "agente-soporte", handler.name)
    async with database.sessions() as db:
        await ApprovalService(db, clock).deprecate("agente-soporte", "1.0.0")
    await drain(fleet)
    run = await load_run(fleet, run_id)
    assert run.status is RunStatus.FAILED
    assert run.failure_reason is not None
    assert run.failure_reason.startswith("admisión denegada:")
    assert handler.executed == 0
    await fleet.stop()


@pytest.mark.requirement("RUN-04", "IDN-03")
async def test_revoked_agent_run_fails_without_executing_steps(
    fleet_settings: Settings, database: Database, clock: FakeClock
) -> None:
    fleet = build_fleet(fleet_settings, database, clock)
    handler = CountingHandler()
    fleet.handlers.register(handler)
    await publish_approved(fleet, build_manifest())
    run_id = await enqueue_run(fleet, "agente-soporte", handler.name)
    async with database.sessions() as db:
        await RevocationService(db, clock).revoke_agent("agente-soporte", "1.0.0")
    await drain(fleet)
    run = await load_run(fleet, run_id)
    assert run.status is RunStatus.FAILED
    assert run.failure_reason is not None
    assert "revocada" in run.failure_reason
    assert handler.executed == 0
    await fleet.stop()


@pytest.mark.requirement("RUN-04")
async def test_approved_agent_run_succeeds_with_a_real_principal(
    fleet_settings: Settings, database: Database, clock: FakeClock
) -> None:
    fleet = build_fleet(fleet_settings, database, clock)
    handler = CountingHandler()
    fleet.handlers.register(handler)
    await publish_approved(fleet, build_manifest())
    run_id = await enqueue_run(fleet, "agente-soporte", handler.name)
    await drain(fleet)
    run = await load_run(fleet, run_id)
    assert run.status is RunStatus.SUCCEEDED
    assert run.output_json == {"agent": "agente-soporte"}
    assert handler.executed == 1
    await fleet.stop()
