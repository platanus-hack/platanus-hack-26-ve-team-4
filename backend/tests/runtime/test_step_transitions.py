from datetime import timedelta

import pytest

from agent_zero.runtime.models import RunStatus
from agent_zero.runtime.repository import RunRepository
from agent_zero.runtime.step_results import Advance, Complete, Fail, Wait
from agent_zero.runtime.step_transitions import apply_result, retry_or_fail
from agent_zero.shared.database import Database
from tests.runtime.support import FakeClock
from tests.runtime.test_repository import make_run


async def test_each_result_maps_to_a_status(database: Database, clock: FakeClock) -> None:
    async with database.sessions() as db:
        repository = RunRepository(db)
        run = await repository.add(make_run("r", RunStatus.RUNNING, clock()))
        await apply_result(repository, run, Advance(checkpoint={"a": 1}), clock())
        assert (run.status, run.step_index, run.checkpoint_json) == (
            RunStatus.QUEUED,
            1,
            {"a": 1},
        )
        until = clock() + timedelta(days=14)
        await apply_result(repository, run, Wait(until=until, checkpoint={"b": 2}), clock())
        assert (run.status, run.resume_at, run.step_index) == (RunStatus.WAITING, until, 2)
        await apply_result(repository, run, Complete(output={"ok": True}), clock())
        assert (run.status, run.output_json, run.resume_at) == (
            RunStatus.SUCCEEDED,
            {"ok": True},
            None,
        )


async def test_fail_result_keeps_step_index(database: Database, clock: FakeClock) -> None:
    async with database.sessions() as db:
        repository = RunRepository(db)
        run = await repository.add(make_run("r", RunStatus.RUNNING, clock()))
        await apply_result(repository, run, Fail(reason="roto"), clock())
        assert (run.status, run.failure_reason, run.step_index) == (RunStatus.FAILED, "roto", 0)


@pytest.mark.requirement("RUN-03")
async def test_retry_until_cap_then_failed(database: Database, clock: FakeClock) -> None:
    async with database.sessions() as db:
        repository = RunRepository(db)
        run = await repository.add(make_run("r", RunStatus.RUNNING, clock()))
        await retry_or_fail(repository, run, TimeoutError("lento"), 3, clock())
        assert (run.status, run.attempts) == (RunStatus.QUEUED, 1)
        await retry_or_fail(repository, run, TimeoutError("lento"), 3, clock())
        assert run.attempts == 2
        await retry_or_fail(repository, run, TimeoutError("lento"), 3, clock())
        assert run.status is RunStatus.FAILED
        assert "reintentos agotados (3/3)" in (run.failure_reason or "")
