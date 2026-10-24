import asyncio
import contextlib

from agent_zero.config import Settings
from agent_zero.runtime.repository import RunRepository
from agent_zero.runtime.step_runner import StepRunner
from agent_zero.runtime.wiring import RuntimeWiring


class RunWorker:
    def __init__(self, wiring: RuntimeWiring, settings: Settings) -> None:
        self._sessions = wiring.sessions
        self._clock = wiring.clock
        self._concurrency = settings.runtime_worker_concurrency
        self._poll_seconds = settings.runtime_poll_seconds
        self._runner = StepRunner(wiring, settings.runtime_max_attempts)
        self._in_flight: set[str] = set()
        self._task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()

    async def run_once(self) -> int:
        async with self._sessions() as db:
            ready = await RunRepository(db).ready_ids(
                self._clock(), frozenset(self._in_flight), self._concurrency
            )
        self._in_flight.update(ready)
        await asyncio.gather(*(self._process(run_id) for run_id in ready))
        return len(ready)

    async def _process(self, run_id: str) -> None:
        try:
            await self._runner.run_step(run_id)
        finally:
            self._in_flight.discard(run_id)

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stopping.clear()
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._stopping.set()
        if self._task is not None:
            await self._task
            self._task = None

    async def _loop(self) -> None:
        while not self._stopping.is_set():
            processed = await self.run_once()
            if processed == 0:
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(self._stopping.wait(), self._poll_seconds)
