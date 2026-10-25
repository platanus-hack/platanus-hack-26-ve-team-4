import asyncio

import pytest

from agent_zero.config import Settings
from agent_zero.llm.errors import ModelLimitReachedError
from agent_zero.llm.models import LimitReason
from agent_zero.runtime.handler_registry import HandlerRegistry
from agent_zero.runtime.handlers import StepContext
from agent_zero.runtime.models import RunStatus
from agent_zero.runtime.repository import RunRepository
from agent_zero.runtime.run_cancel_service import RunCancelService
from agent_zero.runtime.run_worker import RunWorker
from agent_zero.runtime.step_results import Complete, Fail, StepResult
from agent_zero.shared.database import Database
from tests.runtime.flows import (
    advance_step,
    drain,
    enqueue,
    finish,
    new_worker,
    wait_two_weeks,
)
from tests.runtime.support import FakeAdmission, FakeClock, ScriptedHandler


async def status_of(database: Database, run_id: str) -> RunStatus:
    async with database.sessions() as db:
        run = await RunRepository(db).get(run_id)
        assert run is not None
        return run.status


@pytest.mark.requirement("RUN-01")
async def test_queued_run_succeeds_in_background(
    database: Database,
    registry: HandlerRegistry,
    admission: FakeAdmission,
    runtime_settings: Settings,
    clock: FakeClock,
) -> None:
    handler = ScriptedHandler("flujo", [advance_step, finish])
    run_id = await enqueue(database, registry, clock, handler)
    assert await status_of(database, run_id) is RunStatus.QUEUED
    worker = new_worker(database, registry, admission, runtime_settings, clock)
    await drain(worker)
    async with database.sessions() as db:
        run = await RunRepository(db).get(run_id)
    assert run is not None
    assert run.status is RunStatus.SUCCEEDED
    assert run.step_index == 2
    assert run.output_json is not None
    assert handler.calls[0].principal.agent_id == "agente-soporte"
    assert admission.admitted == [("agente-soporte", "1.0.0")] * 2


@pytest.mark.requirement("RUN-01")
async def test_start_stop_loop_processes_runs(
    database: Database,
    registry: HandlerRegistry,
    admission: FakeAdmission,
    runtime_settings: Settings,
    clock: FakeClock,
) -> None:
    handler = ScriptedHandler("flujo", [advance_step, finish])
    run_id = await enqueue(database, registry, clock, handler)
    worker = new_worker(database, registry, admission, runtime_settings, clock)
    worker.start()
    worker.start()
    for _ in range(200):
        if await status_of(database, run_id) is RunStatus.SUCCEEDED:
            break
        await asyncio.sleep(0.01)
    await worker.stop()
    assert await status_of(database, run_id) is RunStatus.SUCCEEDED


@pytest.mark.requirement("RUN-02")
async def test_waiting_run_survives_restart_and_resumes_without_repeating(
    database: Database,
    registry: HandlerRegistry,
    admission: FakeAdmission,
    runtime_settings: Settings,
    clock: FakeClock,
) -> None:
    handler = ScriptedHandler("largo", [advance_step, wait_two_weeks, finish])
    run_id = await enqueue(database, registry, clock, handler)
    await drain(new_worker(database, registry, admission, runtime_settings, clock))
    assert await status_of(database, run_id) is RunStatus.WAITING
    assert [c.step_index for c in handler.calls] == [0, 1]

    reborn = Database(runtime_settings.app_database_url)
    await reborn.create_schema()
    fresh_worker = new_worker(reborn, registry, admission, runtime_settings, clock)
    assert await drain(fresh_worker) == 0
    clock.advance(days=13)
    assert await drain(fresh_worker) == 0
    clock.advance(days=2)
    await drain(fresh_worker)
    async with reborn.sessions() as db:
        run = await RunRepository(db).get(run_id)
    await reborn.dispose()
    assert run is not None
    assert run.status is RunStatus.SUCCEEDED
    assert [c.step_index for c in handler.calls] == [0, 1, 2]
    assert handler.calls[2].checkpoint == {"started": 1}
    assert run.output_json == {"resumed_from": {"started": 1}, "step": 2}


@pytest.mark.requirement("RUN-02")
async def test_orphan_running_run_is_recovered_after_crash(
    database: Database,
    registry: HandlerRegistry,
    admission: FakeAdmission,
    runtime_settings: Settings,
    clock: FakeClock,
) -> None:
    async def crash(_context: StepContext) -> StepResult:
        raise asyncio.CancelledError

    handler = ScriptedHandler("caida", [advance_step, crash, finish])
    run_id = await enqueue(database, registry, clock, handler)
    first = new_worker(database, registry, admission, runtime_settings, clock)
    await first.run_once()
    with pytest.raises(asyncio.CancelledError):
        await first.run_once()
    assert await status_of(database, run_id) is RunStatus.RUNNING

    second = new_worker(database, registry, admission, runtime_settings, clock)
    await drain(second)
    assert await status_of(database, run_id) is RunStatus.SUCCEEDED
    assert handler.calls[-1].step_index == 1
    assert handler.calls[-1].checkpoint == {"visited": [0]}


@pytest.mark.requirement("RUN-03")
async def test_transient_failure_retries_then_succeeds(
    database: Database,
    registry: HandlerRegistry,
    admission: FakeAdmission,
    runtime_settings: Settings,
    clock: FakeClock,
) -> None:
    async def flaky(_context: StepContext) -> StepResult:
        raise TimeoutError("sin respuesta")

    handler = ScriptedHandler("flaky", [flaky, flaky, finish])
    run_id = await enqueue(database, registry, clock, handler)
    await drain(new_worker(database, registry, admission, runtime_settings, clock))
    assert await status_of(database, run_id) is RunStatus.SUCCEEDED
    assert len(handler.calls) == 3


@pytest.mark.requirement("RUN-03")
async def test_transient_failure_stops_at_attempt_cap(
    database: Database,
    registry: HandlerRegistry,
    admission: FakeAdmission,
    runtime_settings: Settings,
    clock: FakeClock,
) -> None:
    async def flaky(_context: StepContext) -> StepResult:
        raise ConnectionError("caído")

    handler = ScriptedHandler("siempre", [flaky])
    run_id = await enqueue(database, registry, clock, handler)
    await drain(new_worker(database, registry, admission, runtime_settings, clock))
    async with database.sessions() as db:
        run = await RunRepository(db).get(run_id)
    assert run is not None
    assert run.status is RunStatus.FAILED
    assert len(handler.calls) == runtime_settings.runtime_max_attempts
    assert "reintentos agotados" in (run.failure_reason or "")


@pytest.mark.requirement("RUN-03")
async def test_limit_reached_is_retried_and_other_errors_fail_fast(
    database: Database,
    registry: HandlerRegistry,
    admission: FakeAdmission,
    runtime_settings: Settings,
    clock: FakeClock,
) -> None:
    async def limited(_context: StepContext) -> StepResult:
        raise ModelLimitReachedError("tope", next(iter(LimitReason)))

    async def broken(_context: StepContext) -> StepResult:
        raise ValueError("bug")

    limited_handler = ScriptedHandler("tope", [limited, finish])
    broken_handler = ScriptedHandler("roto", [broken])
    limited_id = await enqueue(database, registry, clock, limited_handler)
    broken_id = await enqueue(database, registry, clock, broken_handler)
    await drain(new_worker(database, registry, admission, runtime_settings, clock))
    assert await status_of(database, limited_id) is RunStatus.SUCCEEDED
    assert await status_of(database, broken_id) is RunStatus.FAILED
    assert len(broken_handler.calls) == 1


@pytest.mark.requirement("RUN-03")
async def test_cancel_stops_waiting_run_and_in_flight_result_is_discarded(
    database: Database,
    registry: HandlerRegistry,
    admission: FakeAdmission,
    runtime_settings: Settings,
    clock: FakeClock,
) -> None:
    holder: dict[str, str] = {}

    async def cancel_midway(_context: StepContext) -> StepResult:
        async with database.sessions() as db:
            await RunCancelService(db, clock).cancel(holder["id"])
        return Complete(output={"late": True})

    handler = ScriptedHandler("cancelable", [cancel_midway])
    holder["id"] = await enqueue(database, registry, clock, handler)
    await drain(new_worker(database, registry, admission, runtime_settings, clock))
    async with database.sessions() as db:
        run = await RunRepository(db).get(holder["id"])
    assert run is not None
    assert run.status is RunStatus.CANCELLED
    assert run.output_json is None

    waiting = ScriptedHandler("espera", [wait_two_weeks, finish])
    waiting_id = await enqueue(database, registry, clock, waiting)
    worker = new_worker(database, registry, admission, runtime_settings, clock)
    await drain(worker)
    async with database.sessions() as db:
        await RunCancelService(db, clock).cancel(waiting_id)
    clock.advance(days=30)
    await drain(worker)
    assert await status_of(database, waiting_id) is RunStatus.CANCELLED
    assert len(waiting.calls) == 1


@pytest.mark.requirement("RUN-04")
async def test_denied_admission_fails_run_without_executing_steps(
    database: Database,
    registry: HandlerRegistry,
    runtime_settings: Settings,
    clock: FakeClock,
) -> None:
    admission = FakeAdmission({"agente-deprecado": "versión deprecada"})
    handler = ScriptedHandler("flujo", [finish])
    run_id = await enqueue(database, registry, clock, handler, agent_id="agente-deprecado")
    await drain(new_worker(database, registry, admission, runtime_settings, clock))
    async with database.sessions() as db:
        run = await RunRepository(db).get(run_id)
        events = await RunRepository(db).events(run_id)
    assert run is not None
    assert run.status is RunStatus.FAILED
    assert "versión deprecada" in (run.failure_reason or "")
    assert handler.calls == []
    assert events[-1].kind.value == "failed"


@pytest.mark.requirement("RUN-04")
async def test_admission_is_rechecked_before_every_step(
    database: Database,
    registry: HandlerRegistry,
    runtime_settings: Settings,
    clock: FakeClock,
) -> None:
    admission = FakeAdmission()
    handler = ScriptedHandler("revocable", [wait_two_weeks, finish])
    run_id = await enqueue(database, registry, clock, handler)
    worker = new_worker(database, registry, admission, runtime_settings, clock)
    await drain(worker)
    admission.denied["agente-soporte"] = "credencial revocada"
    clock.advance(days=15)
    await drain(worker)
    assert await status_of(database, run_id) is RunStatus.FAILED
    assert len(handler.calls) == 1


async def test_explicit_fail_result_marks_run_failed(
    database: Database,
    registry: HandlerRegistry,
    admission: FakeAdmission,
    runtime_settings: Settings,
    clock: FakeClock,
) -> None:
    async def refuse(_context: StepContext) -> StepResult:
        return Fail(reason="datos inconsistentes")

    run_id = await enqueue(database, registry, clock, ScriptedHandler("rechaza", [refuse]))
    await drain(new_worker(database, registry, admission, runtime_settings, clock))
    assert await status_of(database, run_id) is RunStatus.FAILED


async def test_concurrency_bounds_runs_per_pass(
    database: Database,
    registry: HandlerRegistry,
    admission: FakeAdmission,
    runtime_settings: Settings,
    clock: FakeClock,
) -> None:
    handler = ScriptedHandler("rapido", [finish])
    for _ in range(5):
        await enqueue(database, registry, clock, handler)
    worker: RunWorker = new_worker(database, registry, admission, runtime_settings, clock)
    assert await worker.run_once() == runtime_settings.runtime_worker_concurrency


@pytest.mark.requirement("RUN-01")
async def test_a_slow_run_does_not_hold_back_the_other_slot(
    database: Database,
    registry: HandlerRegistry,
    admission: FakeAdmission,
    runtime_settings: Settings,
    clock: FakeClock,
) -> None:
    release = asyncio.Event()

    async def slow(_: StepContext) -> StepResult:
        await release.wait()
        return Complete(output={"slow": True})

    slow_id = await enqueue(database, registry, clock, ScriptedHandler("lento", [slow]))
    quick_ids = [
        await enqueue(database, registry, clock, ScriptedHandler(f"rapido-{index}", [finish]))
        for index in range(3)
    ]
    worker = new_worker(database, registry, admission, runtime_settings, clock)
    worker.start()
    try:
        for _ in range(300):
            states = {await status_of(database, run_id) for run_id in quick_ids}
            if states == {RunStatus.SUCCEEDED}:
                break
            await asyncio.sleep(0.01)
        assert states == {RunStatus.SUCCEEDED}
        assert await status_of(database, slow_id) is not RunStatus.SUCCEEDED
    finally:
        release.set()
        await worker.stop()
    assert await status_of(database, slow_id) is RunStatus.SUCCEEDED
