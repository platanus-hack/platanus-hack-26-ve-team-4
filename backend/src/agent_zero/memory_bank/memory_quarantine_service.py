from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.memory_bank.memory_cipher import MemoryCipher
from agent_zero.memory_bank.models import MemoryRecord
from agent_zero.shared.clock import utc_now


async def quarantine_matching(
    db: AsyncSession, cipher: MemoryCipher, predicate: Callable[[str], bool]
) -> int:
    count = 0
    for row in await db.scalars(select(MemoryRecord).where(MemoryRecord.expires_at > utc_now())):
        if predicate(cipher.decrypt(row.ciphertext)):
            row.expires_at = utc_now()
            count += 1
    await db.commit()
    return count
