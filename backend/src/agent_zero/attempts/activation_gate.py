from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.policies.models import PolicyStatus
from agent_zero.policies.repository import PolicyRepository


async def activation_pending(db: AsyncSession, now: datetime, hold_seconds: float) -> bool:
    pending = await PolicyRepository(db).pending()
    if pending is None or pending.status is not PolicyStatus.VALIDATING:
        return False
    if pending.validation.get("passed") is not True:
        return False
    validated_at = pending.validation.get("validated_at")
    if not isinstance(validated_at, str):
        return False
    return now - datetime.fromisoformat(validated_at) < timedelta(seconds=hold_seconds)


async def active_version(db: AsyncSession) -> int:
    return (await PolicyRepository(db).active()).version
