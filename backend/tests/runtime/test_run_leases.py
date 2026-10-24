import asyncio
from datetime import timedelta

from sqlalchemy import select

from agent_zero.config import Settings
from agent_zero.runtime.handler_registry import HandlerRegistry
from agent_zero.runtime.handlers import StepContext
from agent_zero.runtime.models import Run, RunLease, RunStatus
from agent_zero.runtime.run_lease import RunLeases
from agent_zero.runtime.step_results import Advance, Complete, StepResult
from agent_zero.runtime.step_runner import StepRunner
from agent_zero.runtime.wiring import RuntimeWiring
from agent_zero.shared.database import Database
from tests.runtime.flows import enqueue, new_worker
from tests.runtime.support import FakeAdmission, FakeClock, ScriptedHandler


async def test_two_workers_cannot_execute_the_same_checkpoint_concurrently(
    database: Database,
    registry: HandlerRegistry,
    admission: FakeAdmission,
    runtime_settings: Settings,
    clock: FakeClock,
) -> None:
    started, release = asyncio.Event(), asyncio.Event()

    async def blocked(context: StepContext) -> StepResult:
        started.set()
        await release.wait()
        return Complete(output={"effect": "once"})

    handler = ScriptedHandler("single-owner", [blocked])
    run_id = await enqueue(database, registry, clock, handler)
    first = new_worker(database, registry, admission, runtime_settings, clock)
    second = new_worker(database, registry, admission, runtime_settings, clock)
    running = asyncio.create_task(first.run_once())
    await asyncio.wait_for(started.wait(), 2)
    try:
        assert await asyncio.wait_for(second.run_once(), 2) == 0
        assert len(handler.calls) == 1
    finally:
        release.set()
    assert await running == 1
    async with database.sessions() as db:
        run = await db.get(Run, run_id)
        assert run is not None
        assert run.status is RunStatus.SUCCEEDED
        assert run.output_json == {"effect": "once"}
        assert await db.get(RunLease, run_id) is None


async def test_expired_owner_cannot_overwrite_recovered_checkpoint(
    database: Database,
    registry: HandlerRegistry,
    admission: FakeAdmission,
    clock: FakeClock,
) -> None:
    async def done(context: StepContext) -> StepResult:
        return Complete(output={})

    run_id = await enqueue(database, registry, clock, ScriptedHandler("recovery-fence", [done]))
    wiring = RuntimeWiring(database.sessions, registry, admission, clock)
    crashed = StepRunner(wiring, 3)
    recovered = StepRunner(wiring, 3)
    old = await crashed._claim(run_id)
    assert old is not None
    assert await recovered._claim(run_id) is None
    clock.advance(seconds=31)
    current = await recovered._claim(run_id)
    assert current is not None
    assert current.lease_owner != old.lease_owner
    await recovered._finish(current, None, result=Advance(checkpoint={"durable": 1}))
    await crashed._finish(old, None, result=Complete(output={"stale": True}))
    # A late cleanup from the crashed owner cannot delete the new owner's lease.
    await RunLeases(database.sessions, clock).release(run_id, old.lease_owner)
    async with database.sessions() as db:
        run = await db.get(Run, run_id)
        lease = await db.get(RunLease, run_id)
        assert run is not None
        assert run.step_index == 1
        assert run.checkpoint_json == {"durable": 1}
        assert run.output_json is None
        assert lease is not None
        assert lease.owner == current.lease_owner


async def test_heartbeat_extends_ownership_during_slow_provider(
    database: Database,
    registry: HandlerRegistry,
    clock: FakeClock,
) -> None:
    async def done(context: StepContext) -> StepResult:
        return Complete(output={})

    run_id = await enqueue(database, registry, clock, ScriptedHandler("slow-step", [done]))
    leases = RunLeases(database.sessions, clock, lease_seconds=0.06)
    claimed = await leases.claim(run_id)
    assert claimed is not None
    _, owner = claimed
    async with leases.maintain(run_id, owner):
        clock.advance(seconds=0.04)
        for _ in range(100):
            async with database.sessions() as db:
                expires = await db.scalar(
                    select(RunLease.expires_at).where(RunLease.run_id == run_id)
                )
            assert expires is not None
            if expires > clock() + timedelta(seconds=0.04):
                break
            await asyncio.sleep(0.005)
        else:
            raise AssertionError("El heartbeat no renovó la reserva")
        clock.advance(seconds=0.03)
        assert await RunLeases(database.sessions, clock).claim(run_id) is None
    async with database.sessions() as db:
        assert await db.get(RunLease, run_id) is None
