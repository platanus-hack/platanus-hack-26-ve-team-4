from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.runtime.models import Run
from agent_zero.runtime.repository import RunRepository


async def query_run(db: AsyncSession, run_id: str) -> Run | None:
    return await RunRepository(db).get(run_id)
