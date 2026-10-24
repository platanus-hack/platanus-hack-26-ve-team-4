import pytest

from agent_zero.runtime.handler_registry import HandlerRegistry, UnknownHandlerError
from agent_zero.runtime.models import RunStatus
from agent_zero.runtime.repository import RunRepository
from agent_zero.runtime.run_enqueue_service import RunEnqueueService
from agent_zero.runtime.schemas import RunCreate
from agent_zero.runtime.step_results import Complete
from agent_zero.shared.database import Database
from tests.runtime.support import FakeClock, ScriptedHandler


async def _done(_context: object) -> Complete:
    return Complete()


def payload(key: str | None = None) -> RunCreate:
    return RunCreate(
        agent_id="a", agent_version="1", handler="h", input={"x": 1}, idempotency_key=key
    )


@pytest.fixture
def ready_registry(registry: HandlerRegistry) -> HandlerRegistry:
    registry.register(ScriptedHandler("h", [_done]))
    return registry


@pytest.mark.requirement("RUN-01")
async def test_enqueue_returns_queued_run_immediately(
    database: Database, ready_registry: HandlerRegistry, clock: FakeClock
) -> None:
    async with database.sessions() as db:
        run = await RunEnqueueService(db, ready_registry, clock).enqueue(payload())
    assert run.run_id.startswith("run-")
    assert run.status is RunStatus.QUEUED
    assert run.input_json == {"x": 1}
    assert run.created_at == clock()


@pytest.mark.requirement("RUN-03")
async def test_same_idempotency_key_returns_same_run(
    database: Database, ready_registry: HandlerRegistry, clock: FakeClock
) -> None:
    async with database.sessions() as db:
        first = await RunEnqueueService(db, ready_registry, clock).enqueue(payload("clave"))
    async with database.sessions() as db:
        second = await RunEnqueueService(db, ready_registry, clock).enqueue(payload("clave"))
        other = await RunEnqueueService(db, ready_registry, clock).enqueue(payload("otra"))
        events = await RunRepository(db).events(first.run_id)
    assert first.run_id == second.run_id
    assert other.run_id != first.run_id
    assert len(events) == 1


@pytest.mark.requirement("RUN-03")
async def test_keyless_enqueues_are_distinct(
    database: Database, ready_registry: HandlerRegistry
) -> None:
    async with database.sessions() as db:
        service = RunEnqueueService(db, ready_registry)
        assert (await service.enqueue(payload())).run_id != (
            await service.enqueue(payload())
        ).run_id


async def test_unknown_handler_is_rejected(database: Database, registry: HandlerRegistry) -> None:
    async with database.sessions() as db:
        with pytest.raises(UnknownHandlerError):
            await RunEnqueueService(db, registry).enqueue(payload())
