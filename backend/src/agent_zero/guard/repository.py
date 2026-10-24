from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.contract.schema import DomainContract, PolicyRule
from agent_zero.guard.models import GuardFindingRecord, GuardPolicyRecord


class IncompatiblePolicyError(ValueError):
    pass


async def active_policy(db: AsyncSession, contract_id: str) -> GuardPolicyRecord | None:
    statement = select(GuardPolicyRecord).where(
        GuardPolicyRecord.contract_id == contract_id, GuardPolicyRecord.status == "active"
    )
    return (await db.execute(statement)).scalar_one_or_none()


async def next_version(db: AsyncSession, contract_id: str) -> int:
    statement = select(func.max(GuardPolicyRecord.version)).where(
        GuardPolicyRecord.contract_id == contract_id
    )
    return int((await db.execute(statement)).scalar_one() or 0) + 1


async def policy(db: AsyncSession, contract_id: str, version: int) -> GuardPolicyRecord | None:
    statement = select(GuardPolicyRecord).where(
        GuardPolicyRecord.contract_id == contract_id, GuardPolicyRecord.version == version
    )
    return (await db.execute(statement)).scalar_one_or_none()


async def policies(db: AsyncSession, contract_id: str) -> list[GuardPolicyRecord]:
    statement = (
        select(GuardPolicyRecord)
        .where(GuardPolicyRecord.contract_id == contract_id)
        .order_by(GuardPolicyRecord.version)
    )
    return list((await db.execute(statement)).scalars())


async def findings(db: AsyncSession, contract_id: str) -> list[GuardFindingRecord]:
    statement = (
        select(GuardFindingRecord)
        .where(GuardFindingRecord.contract_id == contract_id)
        .order_by(GuardFindingRecord.created_at)
    )
    return list((await db.execute(statement)).scalars())


def rules_of(contract: DomainContract, record: GuardPolicyRecord | None) -> list[PolicyRule]:
    if record is None:
        return []
    try:
        return [contract.require_rule(PolicyRule.model_validate(raw)) for raw in record.rules]
    except ValueError as failure:
        raise IncompatiblePolicyError(str(failure)) from failure
