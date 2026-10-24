from datetime import datetime

from agent_zero.runtime.models import Run, RunEventKind, RunStatus
from agent_zero.runtime.repository import RunRepository
from agent_zero.runtime.step_results import Advance, Complete, Fail, StepResult, Wait


async def fail_run(repository: RunRepository, run: Run, reason: str, now: datetime) -> None:
    run.status = RunStatus.FAILED
    run.failure_reason = reason
    run.resume_at = None
    run.updated_at = now
    await repository.add_event(run.run_id, run.step_index, RunEventKind.FAILED, reason, now)


async def retry_or_fail(
    repository: RunRepository, run: Run, error: BaseException, max_attempts: int, now: datetime
) -> None:
    run.attempts += 1
    detail = f"{type(error).__name__}: {error}"
    if run.attempts >= max_attempts:
        reason = f"reintentos agotados ({run.attempts}/{max_attempts}): {detail}"
        await fail_run(repository, run, reason, now)
        return
    run.status = RunStatus.QUEUED
    run.updated_at = now
    await repository.add_event(run.run_id, run.step_index, RunEventKind.RETRY, detail, now)


async def apply_result(
    repository: RunRepository, run: Run, result: StepResult, now: datetime
) -> None:
    if isinstance(result, Fail):
        await fail_run(repository, run, result.reason, now)
        return
    await repository.add_event(run.run_id, run.step_index, RunEventKind.STEP_COMPLETED, "", now)
    run.step_index += 1
    run.attempts = 0
    run.updated_at = now
    if isinstance(result, Complete):
        run.status = RunStatus.SUCCEEDED
        run.output_json = result.output
        run.resume_at = None
        await repository.add_event(run.run_id, run.step_index, RunEventKind.SUCCEEDED, "", now)
    elif isinstance(result, Wait):
        run.status = RunStatus.WAITING
        run.checkpoint_json = result.checkpoint
        run.resume_at = result.until
        await repository.add_event(
            run.run_id, run.step_index, RunEventKind.WAITING, result.until.isoformat(), now
        )
    elif isinstance(result, Advance):
        run.status = RunStatus.QUEUED
        run.checkpoint_json = result.checkpoint
        run.resume_at = None
