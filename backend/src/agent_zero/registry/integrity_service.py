from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.registry.errors import VersionNotFoundError
from agent_zero.registry.hashing import sha256_of
from agent_zero.registry.repository import RegistryRepository
from agent_zero.registry.schemas import IntegrityReport


class IntegrityService:
    def __init__(self, db: AsyncSession) -> None:
        self._repository = RegistryRepository(db)

    async def verify(self, agent_id: str, version: str) -> IntegrityReport:
        row = await self._repository.get(agent_id, version)
        if row is None:
            raise VersionNotFoundError(agent_id, version)
        actual = sha256_of(row.manifest_json)
        return IntegrityReport(
            agent_id=agent_id,
            version=version,
            ok=actual == row.manifest_sha256,
            expected_sha256=row.manifest_sha256,
            actual_sha256=actual,
        )
