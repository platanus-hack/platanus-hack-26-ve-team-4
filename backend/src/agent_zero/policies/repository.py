import hashlib
import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.policies.flow.models import FlowPolicyRecord
from agent_zero.policies.flow.repository import flow_records, flow_view, parse_rules
from agent_zero.policies.models import PolicyPointer, PolicyStatus, PolicyVersion
from agent_zero.policies.validator_catalog import ValidatorName
from agent_zero.shared.clock import utc_now


def content_hash(
    rules: list[str],
    parent_version: int | None = None,
    flow_rules: list[dict[str, Any]] | None = None,
) -> str:
    content: dict[str, Any] = {"rules": sorted(set(rules)), "parent_version": parent_version}
    if flow_rules:
        content["flow_rules"] = sorted(json.dumps(rule, sort_keys=True) for rule in flow_rules)
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def policy_view(row: PolicyVersion, flow: FlowPolicyRecord | None = None) -> dict[str, Any]:
    return flow_view(flow) | {
        "version": row.version,
        "parent_version": row.parent_version,
        "rules": row.rules,
        "content_hash": row.content_hash,
        "status": row.status.value,
        "finding_ids": row.finding_ids,
        "reason": row.reason,
        "validation": row.validation,
        "created_at": row.created_at.isoformat(),
        "activated_at": row.activated_at.isoformat() if row.activated_at else None,
    }


class PolicyRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def initialize(self, *, commit: bool = True) -> None:
        if await self.db.get(PolicyPointer, 1) is None:
            self.db.add(
                PolicyVersion(
                    version=0,
                    parent_version=None,
                    rules=[],
                    content_hash=content_hash([]),
                    status=PolicyStatus.ACTIVE,
                    finding_ids=[],
                    reason="Base del laboratorio.",
                    validation={"passed": True, "baseline": True},
                    created_at=utc_now(),
                    activated_at=utc_now(),
                )
            )
            self.db.add(PolicyPointer(id=1, version=0))
            if commit:
                await self.db.commit()
            else:
                await self.db.flush()

    async def active(self) -> PolicyVersion:
        pointer = await self.db.get(PolicyPointer, 1)
        if pointer is None:
            raise ValueError("No se inicializó la política base.")
        return await self.require(pointer.version)

    async def require(self, version: int) -> PolicyVersion:
        row = await self.db.get(PolicyVersion, version)
        flow = await self.db.get(FlowPolicyRecord, version)
        flow_rules = flow.rules if flow is not None else None
        if flow_rules:
            parse_rules(flow_rules)
        if (
            row is None
            or row.content_hash != content_hash(row.rules, row.parent_version, flow_rules)
            or row.rules != sorted(set(row.rules))
            or not set(row.rules) <= set(ValidatorName)
            or (version == 0 and (row.rules or row.parent_version is not None))
        ):
            raise ValueError("Versión de política inexistente o alterada.")
        return row

    async def next_version(self) -> int:
        return int(await self.db.scalar(select(func.max(PolicyVersion.version))) or 0) + 1

    async def pending(self) -> PolicyVersion | None:
        return await self.db.scalar(
            select(PolicyVersion)
            .where(PolicyVersion.status.in_([PolicyStatus.CANDIDATE, PolicyStatus.VALIDATING]))
            .order_by(PolicyVersion.version)
            .limit(1)
        )

    async def all(self) -> list[dict[str, Any]]:
        rows = await self.db.scalars(select(PolicyVersion).order_by(PolicyVersion.version))
        flows = await flow_records(self.db)
        return [policy_view(row, flows.get(row.version)) for row in rows]

    async def view(self, version: int) -> dict[str, Any]:
        row = await self.require(version)
        return policy_view(row, await self.db.get(FlowPolicyRecord, version))
