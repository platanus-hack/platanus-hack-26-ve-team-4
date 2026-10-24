from agent_zero.fleet.fleet_builder import Fleet
from agent_zero.registry.approval_service import ApprovalService
from agent_zero.registry.publication_service import PublicationService
from agent_zero.registry.schemas import AgentManifest
from agent_zero.runtime.models import Run
from agent_zero.runtime.repository import RunRepository
from agent_zero.runtime.run_enqueue_service import RunEnqueueService
from agent_zero.runtime.schemas import RunCreate


async def publish_approved(fleet: Fleet, manifest: AgentManifest) -> None:
    async with fleet.database.sessions() as db:
        await PublicationService(db, fleet.armor, fleet.clock).publish(manifest)
        await ApprovalService(db, fleet.clock).approve(
            manifest.agent_id, manifest.version, "operador"
        )


async def enqueue_run(fleet: Fleet, agent_id: str, handler: str, key: str | None = None) -> str:
    async with fleet.database.sessions() as db:
        payload = RunCreate(
            agent_id=agent_id, agent_version="1.0.0", handler=handler, idempotency_key=key
        )
        return (await RunEnqueueService(db, fleet.handlers, fleet.clock).enqueue(payload)).run_id


async def drain(fleet: Fleet, limit: int = 50) -> None:
    for _ in range(limit):
        if await fleet.worker.run_once() == 0:
            return
    raise AssertionError("el worker no se estabilizó")


async def load_run(fleet: Fleet, run_id: str) -> Run:
    async with fleet.database.sessions() as db:
        run = await RunRepository(db).get(run_id)
    assert run is not None
    return run
