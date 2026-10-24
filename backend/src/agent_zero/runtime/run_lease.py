import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_zero.arena.round_state import ARENA_HANDLERS, round_resetting
from agent_zero.arena.transactions import serialize_write
from agent_zero.runtime.models import Run, RunLease, RunStatus
from agent_zero.shared.ids import new_id


class RunLeases:
    """Durable per-run exclusion with expiring ownership and checkpoint fencing."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        clock: Callable[[], datetime],
        lease_seconds: float = 30,
    ) -> None:
        self._sessions = sessions
        self._clock = clock
        self._seconds = lease_seconds

    async def claim(self, run_id: str) -> tuple[Run, str] | None:
        async with self._sessions() as db:
            await serialize_write(db)
            run = await db.get(Run, run_id)
            now = self._clock()
            if (
                run is None
                or run.status.terminal
                or (
                    run.status is RunStatus.WAITING
                    and (run.resume_at is None or run.resume_at > now)
                )
            ):
                return None
            if run.handler in ARENA_HANDLERS and await round_resetting(db):
                return None
            lease = await db.get(RunLease, run_id)
            if lease is not None and lease.expires_at > now:
                return None
            owner = new_id("lease")
            expires = now + timedelta(seconds=self._seconds)
            if lease is None:
                db.add(RunLease(run_id=run_id, owner=owner, expires_at=expires))
            else:
                lease.owner = owner
                lease.expires_at = expires
            run.status = RunStatus.RUNNING
            run.updated_at = now
            await db.commit()
            return run, owner

    async def release(self, run_id: str, owner: str) -> None:
        async with self._sessions() as db:
            await db.execute(
                delete(RunLease).where(RunLease.run_id == run_id, RunLease.owner == owner)
            )
            await db.commit()

    async def _renew(self, run_id: str, owner: str, stopping: asyncio.Event) -> None:
        while not stopping.is_set():
            with suppress(TimeoutError):
                await asyncio.wait_for(stopping.wait(), self._seconds / 3)
            if stopping.is_set():
                break
            async with self._sessions() as db:
                renewed = await db.scalar(
                    update(RunLease)
                    .where(RunLease.run_id == run_id, RunLease.owner == owner)
                    .values(expires_at=self._clock() + timedelta(seconds=self._seconds))
                    .returning(RunLease.run_id)
                )
                await db.commit()
            if renewed is None:
                break

    @asynccontextmanager
    async def maintain(self, run_id: str, owner: str) -> AsyncIterator[None]:
        stopping = asyncio.Event()
        heartbeat = asyncio.create_task(self._renew(run_id, owner, stopping))
        try:
            yield
        finally:
            stopping.set()
            try:
                await heartbeat
            finally:
                await self.release(run_id, owner)
