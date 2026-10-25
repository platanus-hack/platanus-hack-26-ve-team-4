import asyncio
import contextlib
import logging

from agent_zero.config import Settings
from agent_zero.runtime.repository import RunRepository
from agent_zero.runtime.step_runner import StepRunner
from agent_zero.runtime.wiring import RuntimeWiring

logger = logging.getLogger(__name__)


class RunWorker:
    def __init__(self, wiring: RuntimeWiring, settings: Settings) -> None:
        self._sessions = wiring.sessions
        self._clock = wiring.clock
        self._concurrency = settings.runtime_worker_concurrency
        self._poll_seconds = settings.runtime_poll_seconds
        self._priority = frozenset(settings.runtime_priority_handlers)
        self._runner = StepRunner(wiring, settings.runtime_max_attempts)
        self._in_flight: set[str] = set()
        self._task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()
        self._tick_lock = asyncio.Lock()

    async def run_once(self) -> int:
        async with self._tick_lock:
            return await self._run_ready()

    async def _claim(self, limit: int) -> list[str]:
        async with self._sessions() as db:
            ready = await RunRepository(db).ready_ids(
                self._clock(), frozenset(self._in_flight), limit, self._priority
            )
        self._in_flight.update(ready)
        return ready

    async def _run_ready(self) -> int:
        ready = await self._claim(self._concurrency)
        processed = await asyncio.gather(*(self._process(run_id) for run_id in ready))
        return sum(processed)

    async def _process(self, run_id: str) -> bool:
        try:
            return await self._runner.run_step(run_id)
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

    async def _fill(self, running: set[asyncio.Task[bool]]) -> None:
        free = self._concurrency - len(running)
        if free <= 0:
            return
        try:
            async with self._tick_lock:
                ready = await self._claim(free)
        except Exception:
            logger.exception("El worker reintentará tras un fallo de infraestructura.")
            return
        running.update(asyncio.create_task(self._process(run_id)) for run_id in ready)

    async def _loop(self) -> None:
        running: set[asyncio.Task[bool]] = set()
        while not self._stopping.is_set():
            await self._fill(running)
            if not running:
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(self._stopping.wait(), self._poll_seconds)
                continue
            done, _ = await asyncio.wait(
                running, timeout=self._poll_seconds, return_when=asyncio.FIRST_COMPLETED
            )
            for task in done:
                running.discard(task)
                if not task.cancelled() and task.exception() is not None:
                    logger.error(
                        "El worker reintentará tras un fallo de infraestructura.",
                        exc_info=task.exception(),
                    )
        if running:
            await asyncio.gather(*running, return_exceptions=True)
