from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.registry.errors import (
    ManifestTamperedError,
    VersionNotApprovedError,
    VersionNotFoundError,
)
from agent_zero.registry.hashing import sha256_of
from agent_zero.registry.models import AgentVersion, VersionStatus
from agent_zero.registry.projection import to_read
from agent_zero.registry.repository import RegistryRepository
from agent_zero.registry.schemas import AgentVersionRead
from agent_zero.registry.semver import semver_key


def _intact(row: AgentVersion) -> bool:
    return sha256_of(row.manifest_json) == row.manifest_sha256


def _latest(rows: list[AgentVersion]) -> AgentVersion:
    return max(rows, key=lambda row: semver_key(row.version))


def _verified(row: AgentVersion) -> AgentVersion:
    if not _intact(row):
        raise ManifestTamperedError(row.agent_id, row.version)
    return row


class DiscoveryService:
    def __init__(self, db: AsyncSession) -> None:
        self._repository = RegistryRepository(db)

    async def discover(
        self,
        capability: str | None = None,
        department: str | None = None,
        tag: str | None = None,
    ) -> list[AgentVersionRead]:
        grouped: dict[str, list[AgentVersion]] = {}
        for row in await self._repository.list_by_status(VersionStatus.APPROVED):
            if _intact(row):
                grouped.setdefault(row.agent_id, []).append(row)
        found = [to_read(_latest(rows)) for rows in grouped.values()]
        wanted_capability = capability.strip().lower() if capability else None
        wanted_tag = tag.strip().lower() if tag else None
        return sorted(
            (
                item
                for item in found
                if (department is None or item.department == department)
                and (wanted_capability is None or wanted_capability in item.manifest.capabilities)
                and (wanted_tag is None or wanted_tag in item.manifest.tags)
            ),
            key=lambda item: item.agent_id,
        )

    async def resolve_latest(self, agent_id: str) -> AgentVersionRead:
        rows = await self._repository.list_for_agent(agent_id, VersionStatus.APPROVED)
        if not rows:
            raise VersionNotFoundError(agent_id)
        return to_read(_verified(_latest(rows)))

    async def resolve(self, agent_id: str, version: str) -> AgentVersionRead:
        row = await self._repository.get(agent_id, version)
        if row is None:
            raise VersionNotFoundError(agent_id, version)
        if row.status is not VersionStatus.APPROVED:
            raise VersionNotApprovedError(agent_id, version, row.status.value)
        return to_read(_verified(row))

    async def read(
        self, agent_id: str, version: str, include_unapproved: bool = True
    ) -> AgentVersionRead:
        row = await self._repository.get(agent_id, version)
        if row is None or (not include_unapproved and row.status is not VersionStatus.APPROVED):
            raise VersionNotFoundError(agent_id, version)
        return to_read(row)
