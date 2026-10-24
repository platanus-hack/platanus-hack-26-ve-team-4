from collections import defaultdict
from collections.abc import Iterable

from pydantic import Field

from agent_zero.llm.models import CallOutcome
from agent_zero.llm.schemas import CallCost, CallRecord, CallUsage, FrozenModel


class RoleUsage(FrozenModel):
    role: str
    calls: int = Field(ge=0)
    outcomes: dict[CallOutcome, int]
    usage: CallUsage
    cost: CallCost
    unpriced_calls: int = Field(ge=0)
    measured_calls: int = Field(ge=0)
    mean_latency_ms: float = Field(ge=0.0)


def _role_usage(role: str, records: list[CallRecord]) -> RoleUsage:
    outcomes = {outcome: 0 for outcome in CallOutcome}
    usage, cost = CallUsage(), CallCost()
    unpriced = 0
    for record in records:
        outcomes[record.outcome] += 1
        if record.usage is not None:
            usage = usage + record.usage
            if record.cost is None:
                unpriced += 1
        if record.cost is not None:
            cost = cost + record.cost
    return RoleUsage(
        role=role,
        calls=len(records),
        outcomes=outcomes,
        usage=usage,
        cost=cost,
        unpriced_calls=unpriced,
        measured_calls=sum(record.measured for record in records),
        mean_latency_ms=sum(record.latency_ms for record in records) / len(records),
    )


def summarize(records: Iterable[CallRecord]) -> list[RoleUsage]:
    by_role: defaultdict[str, list[CallRecord]] = defaultdict(list)
    for record in records:
        by_role[record.role].append(record)
    return [_role_usage(role, by_role[role]) for role in sorted(by_role)]
