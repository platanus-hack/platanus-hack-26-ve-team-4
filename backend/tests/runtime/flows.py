from datetime import timedelta

from agent_zero.config import Settings
from agent_zero.runtime.handler_registry import HandlerRegistry
from agent_zero.runtime.handlers import StepContext
from agent_zero.runtime.run_enqueue_service import RunEnqueueService
from agent_zero.runtime.run_worker import RunWorker
from agent_zero.runtime.schemas import RunCreate
from agent_zero.runtime.step_results import Advance, Complete, StepResult, Wait
from agent_zero.runtime.wiring import RuntimeWiring
from agent_zero.shared.database import Database
from tests.runtime.support import FakeAdmission, FakeClock, ScriptedHandler


async def advance_step(context: StepContext) -> StepResult:
    return Advance(checkpoint={"visited": [*context.checkpoint.get("visited", []), 0]})


async def wait_two_weeks(context: StepContext) -> StepResult:
    return Wait(until=context.now + timedelta(days=14), checkpoint={"started": context.step_index})


async def finish(context: StepContext) -> StepResult:
    return Complete(output={"resumed_from": context.checkpoint, "step": context.step_index})


def new_worker(
    database: Database,
    registry: HandlerRegistry,
    admission: FakeAdmission,
    settings: Settings,
    clock: FakeClock,
) -> RunWorker:
    return RunWorker(RuntimeWiring(database.sessions, registry, admission, clock), settings)


async def enqueue(
    database: Database,
    registry: HandlerRegistry,
    clock: FakeClock,
    handler: ScriptedHandler,
    agent_id: str = "agente-soporte",
) -> str:
    if handler.name not in registry.names():
        registry.register(handler)
    async with database.sessions() as db:
        payload = RunCreate(agent_id=agent_id, agent_version="1.0.0", handler=handler.name)
        return (await RunEnqueueService(db, registry, clock).enqueue(payload)).run_id


async def drain(worker: RunWorker, limit: int = 50) -> int:
    total = 0
    for _ in range(limit):
        processed = await worker.run_once()
        if processed == 0:
            return total
        total += processed
    raise AssertionError("el worker no se estabilizó")
