from datetime import datetime, timedelta

from agent_zero.runtime.models import Run, RunEventKind, RunStatus
from agent_zero.runtime.repository import RunRepository
from agent_zero.shared.database import Database
from tests.runtime.support import FakeClock


def make_run(
    run_id: str, status: RunStatus, now: datetime, resume_at: datetime | None = None
) -> Run:
    return Run(
        run_id=run_id,
        agent_id="a",
        agent_version="1",
        handler="h",
        input_json={},
        status=status,
        resume_at=resume_at,
        checkpoint_json={},
        attempts=0,
        step_index=0,
        created_at=now,
        updated_at=now,
    )


async def test_ready_ids_selects_due_runs_only(database: Database, clock: FakeClock) -> None:
    now = clock()
    async with database.sessions() as db:
        repository = RunRepository(db)
        await repository.add(make_run("queued", RunStatus.QUEUED, now))
        await repository.add(make_run("due", RunStatus.WAITING, now, now - timedelta(seconds=1)))
        await repository.add(make_run("later", RunStatus.WAITING, now, now + timedelta(days=7)))
        await repository.add(make_run("orphan", RunStatus.RUNNING, now))
        await repository.add(make_run("done", RunStatus.SUCCEEDED, now))
        await db.commit()
        ready = await repository.ready_ids(now, frozenset({"orphan"}), 10)
        assert sorted(ready) == ["due", "queued"]
        assert await repository.ready_ids(now, frozenset(), 1) != []
        assert len(await repository.ready_ids(now, frozenset(), 1)) == 1


async def test_get_by_key_and_events(database: Database, clock: FakeClock) -> None:
    async with database.sessions() as db:
        repository = RunRepository(db)
        run = make_run("r1", RunStatus.QUEUED, clock())
        run.idempotency_key = "k"
        await repository.add(run)
        await repository.add_event("r1", 0, RunEventKind.QUEUED, "", clock())
        await repository.add_event("r1", 0, RunEventKind.RETRY, "x", clock())
        await db.commit()
        found = await repository.get_by_key("k")
        assert found is not None
        assert found.run_id == "r1"
        assert await repository.get_by_key("otra") is None
        assert [e.kind for e in await repository.events("r1")] == [
            RunEventKind.QUEUED,
            RunEventKind.RETRY,
        ]
