from collections.abc import Callable
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.armor.model_armor import ModelArmor
from agent_zero.registry.errors import ManifestRejectedError, VersionAlreadyPublishedError
from agent_zero.registry.hashing import canonical_manifest_json, sha256_of
from agent_zero.registry.manifest_screening import screen_manifest
from agent_zero.registry.models import AgentVersion, VersionStatus
from agent_zero.registry.projection import to_read
from agent_zero.registry.repository import RegistryRepository
from agent_zero.registry.schemas import AgentManifest, AgentVersionRead
from agent_zero.shared.clock import utc_now


class PublicationService:
    def __init__(
        self,
        db: AsyncSession,
        armor: ModelArmor | None = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._db = db
        self._armor = armor or ModelArmor()
        self._clock = clock

    def screen(self, manifest: AgentManifest) -> tuple[str, ...]:
        return screen_manifest(manifest, self._armor)

    async def publish(self, manifest: AgentManifest) -> AgentVersionRead:
        reasons = self.screen(manifest)
        if reasons:
            raise ManifestRejectedError(reasons)
        repository = RegistryRepository(self._db)
        if await repository.get(manifest.agent_id, manifest.version) is not None:
            raise VersionAlreadyPublishedError(manifest.agent_id, manifest.version)
        manifest_json = canonical_manifest_json(manifest)
        row = AgentVersion(
            agent_id=manifest.agent_id,
            version=manifest.version,
            department=manifest.department,
            status=VersionStatus.DRAFT,
            manifest_json=manifest_json,
            manifest_sha256=sha256_of(manifest_json),
            published_at=self._clock(),
        )
        try:
            await repository.add(row)
            await self._db.commit()
        except IntegrityError as error:
            await self._db.rollback()
            raise VersionAlreadyPublishedError(manifest.agent_id, manifest.version) from error
        return to_read(row)
