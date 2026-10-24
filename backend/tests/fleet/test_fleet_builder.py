import asyncio
from pathlib import Path

import pytest

from agent_zero.config import Settings
from agent_zero.fleet.fleet_builder import build_fleet
from agent_zero.runtime.handlers import StepContext
from agent_zero.runtime.models import RunStatus
from agent_zero.runtime.step_results import Complete, StepResult
from agent_zero.shared.database import Database
from agent_zero.telemetry.otel_setup import build_telemetry
from tests.agent_gateway.support import build_manifest
from tests.fleet.support import enqueue_run, load_run, publish_approved
from tests.identity.conftest import FakeClock


class QuickHandler:
    name = "rapido"

    async def step(self, context: StepContext) -> StepResult:
        return Complete(output={"ok": True})


@pytest.mark.requirement("RUN-01")
async def test_started_worker_finishes_runs_in_the_background(
    fleet_settings: Settings, database: Database, clock: FakeClock
) -> None:
    fleet = build_fleet(fleet_settings, database, clock)
    fleet.handlers.register(QuickHandler())
    await publish_approved(fleet, build_manifest())
    run_id = await enqueue_run(fleet, "agente-soporte", "rapido")
    fleet.start()
    for _ in range(200):
        if (await load_run(fleet, run_id)).status is RunStatus.SUCCEEDED:
            break
        await asyncio.sleep(0.01)
    await fleet.stop()
    assert (await load_run(fleet, run_id)).status is RunStatus.SUCCEEDED


async def test_stop_without_start_is_safe(fleet_settings: Settings, database: Database) -> None:
    fleet = build_fleet(fleet_settings, database)
    await fleet.stop()


async def test_injected_telemetry_is_not_shut_down(
    fleet_settings: Settings, database: Database
) -> None:
    telemetry = build_telemetry(fleet_settings)
    fleet = build_fleet(fleet_settings, database, telemetry=telemetry)
    assert not fleet.owns_telemetry
    assert fleet.telemetry is telemetry
    await fleet.stop()
    with telemetry.tracer.start_as_current_span("despues"):
        pass
    assert telemetry.memory_exporter is not None
    assert [s.name for s in telemetry.memory_exporter.get_finished_spans()] == ["despues"]


def test_audit_log_lives_under_the_data_dir(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, environment="test")
    assert settings.audit_log_path.parent == tmp_path / "audit"
