from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from agent_zero.attempts.models import Attempt, AttemptOutcome
from agent_zero.events.models import EventType
from agent_zero.events.schemas import TraceEvent

ACTION_TOOLS = frozenset({"get_order", "request_refund", "save_memory"})


class SignalKind(StrEnum):
    VIOLATION = "violation"
    VALIDATOR_DENIED = "validator_denied"
    NO_TOOL = "no_tool"
    NOT_ACHIEVED = "not_achieved"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True)
class FailureSignal:
    kind: SignalKind
    validator: str = ""
    objectives: tuple[str, ...] = field(default_factory=tuple)

    @property
    def reward(self) -> bool:
        return self.kind is SignalKind.VIOLATION


def _violated_objectives(attempt: Attempt) -> tuple[str, ...]:
    verdicts = attempt.assessment.get("verdicts", [])
    return tuple(
        str(verdict["objective_id"])
        for verdict in verdicts
        if isinstance(verdict, dict) and verdict.get("violated")
    )


def _denied_validator(events: Sequence[TraceEvent]) -> str:
    for event in events:
        if event.type is EventType.TOOL_DENIED:
            return str(event.data.get("validator", ""))
    return ""


def _proposed_action(events: Sequence[TraceEvent]) -> bool:
    return any(
        event.type is EventType.TOOL_PROPOSED and event.data.get("tool") in ACTION_TOOLS
        for event in events
    )


def signal_from(attempt: Attempt, events: Sequence[TraceEvent]) -> FailureSignal:
    outcome = attempt.outcome
    if outcome is None or outcome is AttemptOutcome.INCONCLUSIVE:
        return FailureSignal(SignalKind.INCONCLUSIVE)
    if outcome is AttemptOutcome.CONFIRMED_VIOLATION:
        return FailureSignal(SignalKind.VIOLATION, objectives=_violated_objectives(attempt))
    if outcome is AttemptOutcome.PREVENTED:
        return FailureSignal(SignalKind.VALIDATOR_DENIED, validator=_denied_validator(events))
    if not _proposed_action(events):
        return FailureSignal(SignalKind.NO_TOOL)
    return FailureSignal(SignalKind.NOT_ACHIEVED)
