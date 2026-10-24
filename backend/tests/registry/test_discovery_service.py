from collections.abc import Callable

import pytest

from agent_zero.registry.approval_service import ApprovalService
from agent_zero.registry.discovery_service import DiscoveryService
from agent_zero.registry.errors import VersionNotApprovedError, VersionNotFoundError
from agent_zero.registry.publication_service import PublicationService
from agent_zero.registry.schemas import AgentManifest
from agent_zero.shared.database import Database


async def _publish(database: Database, manifest: AgentManifest, approve: bool = True) -> None:
    async with database.sessions() as db:
        await PublicationService(db).publish(manifest)
        if approve:
            await ApprovalService(db).approve(manifest.agent_id, manifest.version, "ana")


@pytest.mark.requirement("REG-04")
async def test_support_finds_finance_agent_by_capability_at_highest_version(
    database: Database, make_manifest: Callable[..., AgentManifest]
) -> None:
    await _publish(database, make_manifest(version="1.2.0"))
    await _publish(database, make_manifest(version="1.10.0"))
    await _publish(database, make_manifest(version="2.0.0"), approve=False)
    await _publish(
        database,
        make_manifest(
            agent_id="agente-soporte", department="soporte", capabilities=("tickets",), tags=()
        ),
    )
    async with database.sessions() as db:
        found = await DiscoveryService(db).discover(capability="Conciliacion")
    assert [(item.agent_id, item.version) for item in found] == [("agente-finanzas", "1.10.0")]


@pytest.mark.requirement("REG-04")
async def test_filters_by_department_tag_and_combination(
    database: Database, make_manifest: Callable[..., AgentManifest]
) -> None:
    await _publish(database, make_manifest())
    await _publish(
        database,
        make_manifest(
            agent_id="agente-soporte",
            department="soporte",
            capabilities=("tickets",),
            tags=("atencion",),
        ),
    )
    async with database.sessions() as db:
        service = DiscoveryService(db)
        everything = await service.discover()
        by_department = await service.discover(department="soporte")
        by_tag = await service.discover(tag="CONTABILIDAD")
        none = await service.discover(department="soporte", capability="conciliacion")
    assert [i.agent_id for i in everything] == ["agente-finanzas", "agente-soporte"]
    assert [i.agent_id for i in by_department] == ["agente-soporte"]
    assert [i.agent_id for i in by_tag] == ["agente-finanzas"]
    assert none == []


@pytest.mark.requirement("REG-03")
async def test_draft_is_not_discovered_or_resolved(
    database: Database, make_manifest: Callable[..., AgentManifest]
) -> None:
    await _publish(database, make_manifest(), approve=False)
    async with database.sessions() as db:
        service = DiscoveryService(db)
        assert await service.discover() == []
        with pytest.raises(VersionNotApprovedError, match="draft"):
            await service.resolve("agente-finanzas", "1.0.0")
        with pytest.raises(VersionNotFoundError):
            await service.resolve_latest("agente-finanzas")


@pytest.mark.requirement("REG-03")
async def test_deprecated_version_stops_resolving(
    database: Database, make_manifest: Callable[..., AgentManifest]
) -> None:
    await _publish(database, make_manifest(version="1.0.0"))
    await _publish(database, make_manifest(version="1.1.0"))
    async with database.sessions() as db:
        await ApprovalService(db).deprecate("agente-finanzas", "1.1.0")
        service = DiscoveryService(db)
        with pytest.raises(VersionNotApprovedError, match="deprecated"):
            await service.resolve("agente-finanzas", "1.1.0")
        assert (await service.resolve_latest("agente-finanzas")).version == "1.0.0"
        assert (await service.read("agente-finanzas", "1.1.0")).status.value == "deprecated"
        with pytest.raises(VersionNotFoundError):
            await service.resolve("agente-finanzas", "9.9.9")
        with pytest.raises(VersionNotFoundError):
            await service.read("agente-finanzas", "9.9.9")
