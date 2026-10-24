from collections.abc import Callable

import pytest
from sqlalchemy import text

from agent_zero.registry.errors import VersionNotFoundError
from agent_zero.registry.integrity_service import IntegrityService
from agent_zero.registry.publication_service import PublicationService
from agent_zero.registry.schemas import AgentManifest
from agent_zero.shared.database import Database


@pytest.mark.requirement("REG-02")
async def test_integrity_ok_then_detects_tampering(
    database: Database, make_manifest: Callable[..., AgentManifest]
) -> None:
    async with database.sessions() as db:
        await PublicationService(db).publish(make_manifest())
        clean = await IntegrityService(db).verify("agente-finanzas", "1.0.0")
    assert clean.ok
    assert clean.expected_sha256 == clean.actual_sha256
    async with database.sessions() as db:
        await db.execute(
            text(
                "UPDATE registry_agent_versions SET manifest_json = replace(manifest_json, "
                "'Concilia', 'Manipula')"
            )
        )
        await db.commit()
        tampered = await IntegrityService(db).verify("agente-finanzas", "1.0.0")
    assert not tampered.ok
    assert tampered.expected_sha256 != tampered.actual_sha256


async def test_integrity_unknown_version(database: Database) -> None:
    async with database.sessions() as db:
        with pytest.raises(VersionNotFoundError):
            await IntegrityService(db).verify("nada", "1.0.0")
