from typing import Any

import pytest

from agent_zero.config import Settings
from agent_zero.identity.schemas import AgentPrincipal
from agent_zero.runtime.handler_registry import HandlerRegistry
from agent_zero.runtime.handlers import StepContext
from agent_zero.runtime.models import RunStatus
from agent_zero.runtime.repository import RunRepository
from agent_zero.runtime.run_worker import RunWorker
from agent_zero.runtime.step_results import Complete, StepResult
from agent_zero.runtime.step_runner import StepRunner
from agent_zero.runtime.tool_access import ToolAccess
from agent_zero.runtime.wiring import RuntimeWiring
from agent_zero.shared.database import Database
from agent_zero.telemetry.otel_setup import build_telemetry
from tests.runtime.flows import advance_step, drain, enqueue, finish, new_worker, wait_two_weeks
from tests.runtime.support import FakeAdmission, FakeClock, ScriptedHandler


async def test_missing_run_is_ignored(
    database: Database, registry: HandlerRegistry, admission: FakeAdmission, clock: FakeClock
) -> None:
    runner = StepRunner(RuntimeWiring(database.sessions, registry, admission, clock), 3)
    await runner.run_step("run-inexistente")


async def test_unregistered_handler_fails_run(
    database: Database,
    registry: HandlerRegistry,
    admission: FakeAdmission,
    runtime_settings: Settings,
    clock: FakeClock,
) -> None:
    handler = ScriptedHandler("efimero", [finish])
    run_id = await enqueue(database, registry, clock, handler)
    empty = HandlerRegistry()
    await drain(
        RunWorker(RuntimeWiring(database.sessions, empty, admission, clock), runtime_settings)
    )
    async with database.sessions() as db:
        run = await RunRepository(db).get(run_id)
    assert run is not None
    assert run.status is RunStatus.FAILED
    assert "No existe un manejador" in (run.failure_reason or "")


@pytest.mark.requirement("RUN-01", "RUN-04")
async def test_spans_per_run_and_step_carry_run_id(
    database: Database,
    registry: HandlerRegistry,
    admission: FakeAdmission,
    runtime_settings: Settings,
    clock: FakeClock,
) -> None:
    telemetry = build_telemetry(runtime_settings.model_copy(update={"otel_exporter": "memory"}))
    handler = ScriptedHandler("traza", [advance_step, finish])
    run_id = await enqueue(database, registry, clock, handler)
    worker = RunWorker(
        RuntimeWiring(database.sessions, registry, admission, clock, telemetry), runtime_settings
    )
    await drain(worker)
    assert telemetry.memory_exporter is not None
    spans = telemetry.memory_exporter.get_finished_spans()
    names = [span.name for span in spans]
    assert names.count("agent_zero.runtime.run") == 2
    assert names.count("agent_zero.runtime.step") == 2
    assert all((span.attributes or {})["agent_zero.run_id"] == run_id for span in spans)
    async with database.sessions() as db:
        run = await RunRepository(db).get(run_id)
    assert run is not None
    assert run.trace_id is not None


class RecordingTools:
    def __init__(self) -> None:
        self.principals: list[str] = []

    def tools_for(self, principal: AgentPrincipal) -> ToolAccess:
        self.principals.append(principal.agent_id)
        return _NullAccess()


class _NullAccess:
    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any], data_region: str | None = None
    ) -> str:
        return tool_name


async def test_step_context_receives_tool_access_for_the_principal(
    database: Database,
    registry: HandlerRegistry,
    admission: FakeAdmission,
    runtime_settings: Settings,
    clock: FakeClock,
) -> None:
    seen: list[ToolAccess | None] = []

    async def capture(context: StepContext) -> StepResult:
        seen.append(context.tools)
        return Complete(output={})

    provider = RecordingTools()
    await enqueue(database, registry, clock, ScriptedHandler("con-acceso", [capture]))
    worker = RunWorker(
        RuntimeWiring(database.sessions, registry, admission, clock, tools=provider),
        runtime_settings,
    )
    await drain(worker)
    assert provider.principals == ["agente-soporte"]
    assert seen[0] is not None


async def test_step_context_has_no_tools_without_provider(
    database: Database,
    registry: HandlerRegistry,
    admission: FakeAdmission,
    runtime_settings: Settings,
    clock: FakeClock,
) -> None:
    seen: list[ToolAccess | None] = []

    async def capture(context: StepContext) -> StepResult:
        seen.append(context.tools)
        return Complete(output={})

    await enqueue(database, registry, clock, ScriptedHandler("sin-acceso", [capture]))
    await drain(new_worker(database, registry, admission, runtime_settings, clock))
    assert seen == [None]


@pytest.mark.requirement("OBS-01")
async def test_resumed_steps_continue_the_first_trace(
    database: Database,
    registry: HandlerRegistry,
    admission: FakeAdmission,
    runtime_settings: Settings,
    clock: FakeClock,
) -> None:
    telemetry = build_telemetry(runtime_settings.model_copy(update={"otel_exporter": "memory"}))
    handler = ScriptedHandler("larga", [wait_two_weeks, finish])
    await enqueue(database, registry, clock, handler)
    worker = RunWorker(
        RuntimeWiring(database.sessions, registry, admission, clock, telemetry), runtime_settings
    )
    await drain(worker)
    clock.advance(days=15)
    await drain(worker)
    assert telemetry.memory_exporter is not None
    spans = telemetry.memory_exporter.get_finished_spans()
    assert len(spans) == 4
    assert len({span.context.trace_id for span in spans if span.context}) == 1
