from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.policies.flow.dsl import FlowRule
from agent_zero.policies.flow.models import FlowPolicyRecord
from agent_zero.policies.flow.render import render


def parse_rules(raw: list[dict[str, Any]]) -> list[FlowRule]:
    try:
        return [FlowRule.model_validate(item) for item in raw]
    except ValidationError as error:
        raise ValueError("Reglas de flujo alteradas.") from error


def flow_view(record: FlowPolicyRecord | None) -> dict[str, Any]:
    if record is None:
        return {"flow_rules": [], "synthesis": None}
    rules = parse_rules(record.rules)
    return {
        "flow_rules": [rule.model_dump(mode="json") | {"text": render(rule)} for rule in rules],
        "synthesis": record.synthesis or None,
    }


async def flow_rules(db: AsyncSession, version: int) -> list[FlowRule]:
    record = await db.get(FlowPolicyRecord, version)
    return parse_rules(record.rules) if record is not None else []


async def flow_records(db: AsyncSession) -> dict[int, FlowPolicyRecord]:
    return {row.version: row for row in await db.scalars(select(FlowPolicyRecord))}
