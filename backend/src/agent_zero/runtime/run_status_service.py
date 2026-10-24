from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.runtime.models import Run, RunStatus


@dataclass(frozen=True)
class RunState:
    """Lo que otro dominio necesita saber de un run, sin acceder a su repositorio."""

    run_id: str
    status: RunStatus
    output: dict[str, Any] | None
    failure_reason: str | None

    @property
    def started(self) -> bool:
        return self.status is not RunStatus.QUEUED

    @property
    def terminal(self) -> bool:
        return self.status.terminal

    @property
    def succeeded(self) -> bool:
        return self.status is RunStatus.SUCCEEDED


async def read_run_states(db: AsyncSession, run_ids: Sequence[str]) -> dict[str, RunState]:
    if not run_ids:
        return {}
    runs = await db.scalars(select(Run).where(Run.run_id.in_(run_ids)))
    return {
        run.run_id: RunState(run.run_id, run.status, run.output_json, run.failure_reason)
        for run in runs
    }
