import pytest
from sqlalchemy import text

from agent_zero.agent_gateway.manifest_source import RegistryManifestSource
from agent_zero.registry.approval_service import ApprovalService
from agent_zero.registry.publication_service import PublicationService
from agent_zero.shared.database import Database
from tests.agent_gateway.support import build_manifest
from tests.identity.conftest import FakeClock


@pytest.mark.requirement("REG-03")
async def test_only_approved_versions_expose_tool_grants(
    database: Database, clock: FakeClock
) -> None:
    source = RegistryManifestSource(database.sessions)
    manifest = build_manifest()
    assert await source.tool_grants("agente-soporte", "1.0.0") is None
    async with database.sessions() as db:
        await PublicationService(db, clock=clock).publish(manifest)
    assert await source.tool_grants("agente-soporte", "1.0.0") is None
    async with database.sessions() as db:
        await ApprovalService(db, clock).approve("agente-soporte", "1.0.0", "operador")
    grants = await source.tool_grants("agente-soporte", "1.0.0")
    assert grants is not None
    assert set(grants) == {"get_order"}
    async with database.sessions() as db:
        await ApprovalService(db, clock).deprecate("agente-soporte", "1.0.0")
    assert await source.tool_grants("agente-soporte", "1.0.0") is None


@pytest.mark.requirement("REG-02")
async def test_tampered_manifest_exposes_no_tool_grants(
    database: Database, clock: FakeClock
) -> None:
    async with database.sessions() as db:
        await PublicationService(db, clock=clock).publish(build_manifest())
        await ApprovalService(db, clock).approve("agente-soporte", "1.0.0", "operador")
    source = RegistryManifestSource(database.sessions)
    assert await source.tool_grants("agente-soporte", "1.0.0") is not None
    async with database.sessions() as db:
        await db.execute(
            text(
                "UPDATE registry_agent_versions SET manifest_json = "
                "replace(manifest_json, 'get_order', 'drop_tables')"
            )
        )
        await db.commit()
    assert await source.tool_grants("agente-soporte", "1.0.0") is None
