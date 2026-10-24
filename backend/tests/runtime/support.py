from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from agent_zero.identity.schemas import AgentPrincipal
from agent_zero.runtime.admission import AdmissionDeniedError
from agent_zero.runtime.handlers import StepContext
from agent_zero.runtime.step_results import StepResult
from agent_zero.shared.classification import DataClassification


class FakeClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float = 0, days: float = 0) -> None:
        self.now += timedelta(seconds=seconds, days=days)


StepFn = Callable[[StepContext], Awaitable[StepResult]]


class ScriptedHandler:
    def __init__(self, name: str, steps: list[StepFn]) -> None:
        self.name = name
        self.steps = steps
        self.calls: list[StepContext] = []

    async def step(self, context: StepContext) -> StepResult:
        self.calls.append(context)
        index = min(len(self.calls) - 1, len(self.steps) - 1)
        return await self.steps[index](context)


class FakeAdmission:
    def __init__(self, denied: dict[str, str] | None = None) -> None:
        self.denied = denied or {}
        self.admitted: list[tuple[str, str]] = []

    async def admit(self, agent_id: str, version: str) -> AgentPrincipal:
        if agent_id in self.denied:
            raise AdmissionDeniedError(self.denied[agent_id])
        self.admitted.append((agent_id, version))
        now = datetime(2026, 10, 24, tzinfo=UTC)
        return AgentPrincipal(
            credential_id="cred-1",
            agent_id=agent_id,
            version=version,
            department="soporte",
            scopes=("tool:get_order",),
            clearance=DataClassification.INTERNAL,
            allowed_regions=("cl",),
            issued_at=now,
            expires_at=now + timedelta(days=1),
        )
