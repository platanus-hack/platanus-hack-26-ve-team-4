import pytest

from agent_zero.registry.errors import VersionAlreadyPublishedError
from agent_zero.registry.publication_service import PublicationService
from agent_zero.registry.repository import RegistryRepository
from agent_zero.shared.database import Database
from agent_zero.victim.arena_manifest import ARENA_VERSION, arena_manifest
from agent_zero.victim.honeytool_schemas import HONEYTOOL_MODELS
from tests.registry.conftest import FakeClock, clock, database, registry_settings

__all__ = ["clock", "database", "registry_settings"]

PREVIOUS_VERSION = "2.0.0"


async def test_an_existing_database_gets_the_new_version_next_to_the_old_one(
    database: Database, clock: FakeClock
) -> None:
    old = arena_manifest(decoy=True).model_copy(update={"version": PREVIOUS_VERSION})
    async with database.sessions() as db:
        await PublicationService(db, clock=clock).publish(old)
    async with database.sessions() as db:
        await PublicationService(db, clock=clock).publish(arena_manifest(decoy=True))
    async with database.sessions() as db:
        with pytest.raises(VersionAlreadyPublishedError):
            await PublicationService(db, clock=clock).publish(arena_manifest(decoy=True))
    async with database.sessions() as db:
        stored = await RegistryRepository(db).get("soporte-senuelo", ARENA_VERSION)

    assert ARENA_VERSION != PREVIOUS_VERSION
    assert stored is not None
    assert all(name in stored.manifest_json for name in HONEYTOOL_MODELS)
