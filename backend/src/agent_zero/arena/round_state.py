from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.arena.round_models import RoundArchive

ARENA_HANDLERS = frozenset(
    {"arena_attempt", "validate_patch", "prober_campaign", "broad_evaluation", "finding_analysis"}
)


async def round_resetting(db: AsyncSession) -> bool:
    return (
        await db.scalar(select(RoundArchive.id).where(RoundArchive.status == "resetting").limit(1))
        is not None
    )
