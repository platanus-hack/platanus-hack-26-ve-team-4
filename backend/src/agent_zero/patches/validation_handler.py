from agent_zero.attempts.attempt_query_service import AttemptQueryService
from agent_zero.events.event_store import EventStore
from agent_zero.patches.explanation import PatchExplainer
from agent_zero.patches.validation_runner import ValidationRunner
from agent_zero.policies.policy_service import PolicyService
from agent_zero.runtime.handlers import StepContext
from agent_zero.runtime.step_results import Complete, Fail, StepResult
from agent_zero.victim.arena_manifest import PATCH_HANDLER


class PatchValidationHandler:
    name = PATCH_HANDLER

    def __init__(
        self,
        policies: PolicyService,
        attempts: AttemptQueryService,
        events: EventStore,
        validator: ValidationRunner,
        explainer: PatchExplainer | None = None,
    ) -> None:
        self._policies = policies
        self._attempts = attempts
        self._events = events
        self._validator = validator
        self._explainer = explainer

    async def step(self, context: StepContext) -> StepResult:
        version = int(context.input["version"])
        if not await self._policies.start_validation(version):
            return Complete(output={"version": version, "skipped": True})
        attempt = await self._attempts.get(str(context.input["attempt_id"]))
        if attempt is None:
            return Fail(reason="No existe el intento original del parche.")
        if self._explainer is not None:
            await self._explainer.explain(version, attempt)
        report = await self._validator.validate(
            version,
            attempt,
            await self._events.for_attempt(attempt.id),
            str(context.input["objective_id"]),
        )
        await self._policies.record_validation(version, report)
        return Complete(output=report)
