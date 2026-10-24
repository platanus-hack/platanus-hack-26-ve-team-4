from dataclasses import dataclass
from typing import Any

from agent_zero.llm.errors import ModelLimitReachedError, transient
from agent_zero.runtime.admission import AdmissionDeniedError
from agent_zero.runtime.handler_registry import UnknownHandlerError
from agent_zero.runtime.handlers import StepContext
from agent_zero.runtime.models import Run, RunStatus
from agent_zero.runtime.repository import RunRepository
from agent_zero.runtime.run_tracing import current_trace_id, resumed_trace, run_span
from agent_zero.runtime.step_results import StepResult
from agent_zero.runtime.step_transitions import apply_result, fail_run, retry_or_fail
from agent_zero.runtime.wiring import RuntimeWiring


@dataclass(frozen=True)
class StepSnapshot:
    agent_id: str
    version: str
    handler: str
    input: dict[str, Any]
    checkpoint: dict[str, Any]
    step_index: int
    trace_id: str | None


class StepRunner:
    def __init__(self, wiring: RuntimeWiring, max_attempts: int) -> None:
        self._sessions = wiring.sessions
        self._registry = wiring.registry
        self._admission = wiring.admission
        self._clock = wiring.clock
        self._telemetry = wiring.telemetry
        self._tools = wiring.tools
        self._max_attempts = max_attempts

    async def run_step(self, run_id: str) -> None:
        snapshot = await self._claim(run_id)
        if snapshot is None:
            return
        agent_id = snapshot.agent_id
        with (
            resumed_trace(snapshot.trace_id),
            run_span(self._telemetry, "runtime.run", run_id, agent_id) as run_scope,
        ):
            trace_id = snapshot.trace_id or current_trace_id(run_scope)
            with run_span(self._telemetry, "runtime.step", run_id, agent_id, snapshot.step_index):
                try:
                    principal = await self._admission.admit(agent_id, snapshot.version)
                except AdmissionDeniedError as denial:
                    await self._finish(
                        run_id, trace_id, failure=f"admisión denegada: {denial.reason}"
                    )
                    return
                try:
                    handler = self._registry.get(snapshot.handler)
                except UnknownHandlerError as unknown:
                    await self._finish(run_id, trace_id, failure=str(unknown))
                    return
                context = StepContext(
                    run_id=run_id,
                    input=snapshot.input,
                    checkpoint=snapshot.checkpoint,
                    step_index=snapshot.step_index,
                    principal=principal,
                    now=self._clock(),
                    tools=self._tools.tools_for(principal) if self._tools else None,
                )
                try:
                    result = await handler.step(context)
                except Exception as error:
                    if transient(error) or isinstance(error, ModelLimitReachedError):
                        await self._finish(run_id, trace_id, retry=error)
                    else:
                        reason = f"error no recuperable: {type(error).__name__}: {error}"
                        await self._finish(run_id, trace_id, failure=reason)
                    return
                await self._finish(run_id, trace_id, result=result)

    async def _claim(self, run_id: str) -> StepSnapshot | None:
        async with self._sessions() as db:
            run = await RunRepository(db).get(run_id)
            if run is None or run.status.terminal:
                return None
            run.status = RunStatus.RUNNING
            run.updated_at = self._clock()
            await db.commit()
            return StepSnapshot(
                agent_id=run.agent_id,
                version=run.agent_version,
                handler=run.handler,
                input=dict(run.input_json),
                checkpoint=dict(run.checkpoint_json),
                step_index=run.step_index,
                trace_id=run.trace_id,
            )

    async def _finish(
        self,
        run_id: str,
        trace_id: str | None,
        result: StepResult | None = None,
        failure: str | None = None,
        retry: BaseException | None = None,
    ) -> None:
        async with self._sessions() as db:
            repository = RunRepository(db)
            run = await repository.get(run_id)
            if run is None or run.status is RunStatus.CANCELLED:
                return
            now = self._clock()
            self._stamp_trace(run, trace_id)
            if failure is not None:
                await fail_run(repository, run, failure, now)
            elif retry is not None:
                await retry_or_fail(repository, run, retry, self._max_attempts, now)
            elif result is not None:
                await apply_result(repository, run, result, now)
            await db.commit()

    @staticmethod
    def _stamp_trace(run: Run, trace_id: str | None) -> None:
        if run.trace_id is None and trace_id is not None:
            run.trace_id = trace_id
