import pytest

from agent_zero.runtime.models import RunStatus
from agent_zero.runtime.repository import RunRepository
from agent_zero.runtime.run_cancel_service import RunCancelService, RunNotFoundError
from agent_zero.shared.database import Database
from tests.runtime.support import FakeClock
from tests.runtime.test_repository import make_run


@pytest.mark.requirement("RUN-03")
async def test_cancel_marks_run_cancelled_and_clears_wait(
    database: Database, clock: FakeClock
) -> None:
    async with database.sessions() as db:
        await RunRepository(db).add(make_run("r", RunStatus.WAITING, clock(), clock()))
        await db.commit()
        run = await RunCancelService(db, clock).cancel("r")
        assert run.status is RunStatus.CANCELLED
        assert run.resume_at is None
        events = await RunRepository(db).events("r")
    assert [e.kind.value for e in events] == ["cancelled"]


async def test_cancel_terminal_run_is_noop(database: Database, clock: FakeClock) -> None:
    async with database.sessions() as db:
        await RunRepository(db).add(make_run("r", RunStatus.SUCCEEDED, clock()))
        await db.commit()
        run = await RunCancelService(db, clock).cancel("r")
    assert run.status is RunStatus.SUCCEEDED


async def test_cancel_unknown_run_raises(database: Database) -> None:
    async with database.sessions() as db:
        with pytest.raises(RunNotFoundError, match="No existe la ejecución"):
            await RunCancelService(db).cancel("nada")
