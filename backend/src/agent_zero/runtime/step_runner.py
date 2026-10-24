from typing import Any

from agent_zero.llm.errors import ModelLimitReachedError, transient
from agent_zero.runtime.admission import AdmissionDeniedError
from agent_zero.runtime.handler_registry import UnknownHandlerError
from agent_zero.runtime.handlers import StepContext
from agent_zero.runtime.models import Run, RunStatus
from agent_zero.runtime.repository import RunRepository
from agent_zero.runtime.run_tracing import current_trace_id, run_span
from agent_zero.runtime.step_results import StepResult
from agent_zero.runtime.step_transitions import apply_result, fail_run, retry_or_fail
from agent_zero.runtime.wiring import RuntimeWiring


class StepRunner:
    def __init__(self, wiring: RuntimeWiring, max_attempts: int) -> None:
        self._sessions = wiring.sessions
        self._registry = wiring.registry
        self._admission = wiring.admission
        self._clock = wiring.clock
        self._telemetry = wiring.telemetry
        self._max_attempts = max_attempts

    async def run_step(self, run_id: str) -> None:
        snapshot = await self._claim(run_id)
        if snapshot is None:
            return
        agent_id, version, handler_name, run_input, checkpoint, step_index = snapshot
        with run_span(self._telemetry, "runtime.run", run_id, agent_id) as run_scope:
            trace_id = current_trace_id(run_scope)
            with run_span(self._telemetry, "runtime.step", run_id, agent_id, step_index):
                try:
                    principal = await self._admission.admit(agent_id, version)
                except AdmissionDeniedError as denial:
                    await self._finish(
                        run_id, trace_id, failure=f"admisión denegada: {denial.reason}"
                    )
                    return
                try:
                    handler = self._registry.get(handler_name)
                except UnknownHandlerError as unknown:
                    await self._finish(run_id, trace_id, failure=str(unknown))
                    return
                context = StepContext(
                    run_id=run_id,
                    input=run_input,
                    checkpoint=checkpoint,
                    step_index=step_index,
                    principal=principal,
                    now=self._clock(),
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

    async def _claim(
        self, run_id: str
    ) -> tuple[str, str, str, dict[str, Any], dict[str, Any], int] | None:
        async with self._sessions() as db:
            run = await RunRepository(db).get(run_id)
            if run is None or run.status.terminal:
                return None
            run.status = RunStatus.RUNNING
            run.updated_at = self._clock()
            await db.commit()
            return (
                run.agent_id,
                run.agent_version,
                run.handler,
                dict(run.input_json),
                dict(run.checkpoint_json),
                run.step_index,
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
