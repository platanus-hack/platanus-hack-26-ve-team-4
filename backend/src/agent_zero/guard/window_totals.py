from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.contract.conditions import Condition, WindowExceeds, number_of
from agent_zero.contract.schema import DomainContract, PolicyRule
from agent_zero.guard.models import GuardCallRecord


def window_conditions(
    contract: DomainContract, tool: str, rules: Iterable[PolicyRule]
) -> list[WindowExceeds]:
    candidates: list[Condition] = [
        invariant.never for invariant in contract.invariants if tool in invariant.tools
    ]
    candidates.extend(rule.deny_when for rule in rules if rule.tool == tool)
    unique = {
        condition.total_key(): condition
        for condition in candidates
        if isinstance(condition, WindowExceeds)
    }
    return list(unique.values())


async def window_totals(
    db: AsyncSession,
    contract_id: str,
    subject: str,
    tool: str,
    conditions: Iterable[WindowExceeds],
) -> dict[str, float]:
    moment = datetime.now(UTC)
    totals: dict[str, float] = {}
    for condition in conditions:
        statement = select(GuardCallRecord.facts).where(
            GuardCallRecord.contract_id == contract_id,
            GuardCallRecord.subject == subject,
            GuardCallRecord.tool == tool,
            GuardCallRecord.allowed.is_(True),
            GuardCallRecord.created_at >= moment - timedelta(seconds=condition.window_seconds),
        )
        total = 0.0
        for facts in (await db.execute(statement)).scalars():
            value = number_of(facts.get("arguments", {}).get(condition.argument))
            total += value or 0.0
        totals[condition.total_key()] = total
    return totals
