from collections.abc import Iterable
from dataclasses import dataclass

from agent_zero.policies.validator_catalog import ValidatorName

ORDER_TOOLS = frozenset({"get_order", "request_refund"})
DENIAL_WEIGHTS: dict[str, int] = {
    ValidatorName.ORDER_OWNER: 3,
    ValidatorName.REFUND_LIMIT: 2,
    ValidatorName.MEMORY_KEYS: 2,
    ValidatorName.PROVENANCE: 2,
    "valid_call_context": 1,
}
FLOW_WEIGHT = 2
MISSING_ORDER_WEIGHT = 1
ENUMERATION_WEIGHT = 2
ENUMERATION_DISTINCT_ORDERS = 3
NEAR_MISS_DISTANCE = 1


@dataclass(frozen=True)
class ToolOutcome:
    tool: str
    denied: bool
    validator: str | None
    order_id: str | None


def _distance(left: str, right: str) -> int:
    rows = [list(range(len(right) + 1))]
    for i, char in enumerate(left, start=1):
        row = [i]
        for j, other in enumerate(right, start=1):
            cost = min(rows[-1][j] + 1, row[-1] + 1, rows[-1][j - 1] + (char != other))
            if i > 1 and j > 1 and char == right[j - 2] and left[i - 2] == other:
                cost = min(cost, rows[-2][j - 2] + 1)
            row.append(cost)
        rows.append(row)
    return rows[-1][-1]


def _normalize(order_id: str) -> str:
    return "".join(order_id.split()).upper()


def is_near_miss(order_id: str, own_orders: Iterable[str]) -> bool:
    candidate = _normalize(order_id)
    return any(
        candidate[:1] == own[:1] and _distance(candidate, own) <= NEAR_MISS_DISTANCE
        for own in map(_normalize, own_orders)
    )


def _denial_points(outcome: ToolOutcome, own: frozenset[str]) -> int:
    validator = outcome.validator or ""
    if validator == "order_exists":
        return 0 if _is_typo(outcome, own) else MISSING_ORDER_WEIGHT
    if validator.startswith("flow:"):
        return FLOW_WEIGHT
    return DENIAL_WEIGHTS.get(validator, 0)


def _is_typo(outcome: ToolOutcome, own: frozenset[str]) -> bool:
    return (
        outcome.validator == "order_exists"
        and outcome.order_id is not None
        and is_near_miss(outcome.order_id, own)
    )


def _foreign_orders(outcomes: Iterable[ToolOutcome], own: frozenset[str]) -> set[str]:
    return {
        _normalize(outcome.order_id)
        for outcome in outcomes
        if outcome.tool in ORDER_TOOLS
        and outcome.order_id
        and _normalize(outcome.order_id) not in own
        and not _is_typo(outcome, own)
    }


def risk_score(outcomes: list[ToolOutcome], own_orders: Iterable[str]) -> int:
    own = frozenset(_normalize(order) for order in own_orders)
    points = sum(_denial_points(outcome, own) for outcome in outcomes if outcome.denied)
    if len(_foreign_orders(outcomes, own)) >= ENUMERATION_DISTINCT_ORDERS:
        points += ENUMERATION_WEIGHT
    return points
