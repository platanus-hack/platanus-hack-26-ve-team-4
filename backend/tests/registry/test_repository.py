from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from agent_zero.registry.hashing import canonical_manifest_json, sha256_of
from agent_zero.registry.models import AgentVersion, VersionStatus
from agent_zero.registry.repository import RegistryRepository
from agent_zero.registry.schemas import AgentManifest
from agent_zero.shared.database import Database


def _row(manifest: AgentManifest, status: VersionStatus) -> AgentVersion:
    body = canonical_manifest_json(manifest)
    return AgentVersion(
        agent_id=manifest.agent_id,
        version=manifest.version,
        department=manifest.department,
        status=status,
        manifest_json=body,
        manifest_sha256=sha256_of(body),
        published_at=datetime(2026, 10, 24, tzinfo=UTC),
    )


@pytest.mark.requirement("REG-01")
async def test_persists_and_reads_from_fresh_session(
    database: Database, make_manifest: Callable[..., AgentManifest]
) -> None:
    async with database.sessions() as db:
        await RegistryRepository(db).add(_row(make_manifest(), VersionStatus.DRAFT))
        await db.commit()
    async with database.sessions() as db:
        stored = await RegistryRepository(db).get("agente-finanzas", "1.0.0")
    assert stored is not None
    assert stored.status is VersionStatus.DRAFT
    assert AgentManifest.model_validate_json(stored.manifest_json).department == "finanzas"


async def test_lists_filter_by_status_and_agent(
    database: Database, make_manifest: Callable[..., AgentManifest]
) -> None:
    async with database.sessions() as db:
        repository = RegistryRepository(db)
        await repository.add(_row(make_manifest(version="1.0.0"), VersionStatus.APPROVED))
        await repository.add(_row(make_manifest(version="1.1.0"), VersionStatus.DRAFT))
        await repository.add(_row(make_manifest(agent_id="otro"), VersionStatus.APPROVED))
        await db.commit()
        approved = await repository.list_by_status(VersionStatus.APPROVED)
        own = await repository.list_for_agent("agente-finanzas")
        own_approved = await repository.list_for_agent("agente-finanzas", VersionStatus.APPROVED)
        assert await repository.get("nada", "1.0.0") is None
    assert len(approved) == 2
    assert len(own) == 2
    assert [r.version for r in own_approved] == ["1.0.0"]
