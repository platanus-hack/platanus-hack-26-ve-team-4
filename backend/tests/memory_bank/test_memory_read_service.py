import pytest

from agent_zero.config import Settings
from agent_zero.identity.errors import IdentityDeniedError
from agent_zero.memory_bank.memory_cipher import MemoryCipher
from agent_zero.memory_bank.memory_read_service import MemoryReadService
from agent_zero.memory_bank.memory_write_service import MemoryWriteService
from agent_zero.memory_bank.models import MemoryKind
from agent_zero.shared.database import Database
from tests.identity.conftest import FakeClock
from tests.memory_bank.conftest import PrincipalFactory, make_request
from tests.memory_bank.support import ScopeOnlyGuard


@pytest.mark.requirement("MEM-01")
async def test_memory_survives_new_database_instance_days_later(
    memory_settings: Settings,
    cipher: MemoryCipher,
    clock: FakeClock,
    make_principal: PrincipalFactory,
) -> None:
    first = Database(memory_settings.app_database_url)
    await first.create_schema()
    async with first.sessions() as db:
        await MemoryWriteService(db, memory_settings, cipher, ScopeOnlyGuard(), clock=clock).write(
            make_principal(),
            make_request("El cliente prefiere factura electrónica", run_id="run-A"),
        )
    await first.dispose()

    clock.advance(5 * 86400)
    second = Database(memory_settings.app_database_url)
    await second.create_schema()
    async with second.sessions() as db:
        items = await MemoryReadService(db, cipher, ScopeOnlyGuard(), clock).recall(
            make_principal(), "cliente-1"
        )
    await second.dispose()
    assert [item.content for item in items] == ["El cliente prefiere factura electrónica"]
    assert items[0].source_run_id == "run-A"


@pytest.mark.requirement("MEM-02")
async def test_isolation_by_agent_and_subject(
    database: Database,
    memory_settings: Settings,
    cipher: MemoryCipher,
    clock: FakeClock,
    make_principal: PrincipalFactory,
) -> None:
    async with database.sessions() as db:
        await MemoryWriteService(db, memory_settings, cipher, ScopeOnlyGuard(), clock=clock).write(
            make_principal(), make_request()
        )
        reader = MemoryReadService(db, cipher, ScopeOnlyGuard(), clock)
        assert await reader.recall(make_principal(agent_id="agent-otro"), "cliente-1") == []
        assert await reader.recall(make_principal(), "cliente-2") == []
        assert len(await reader.recall(make_principal(), "cliente-1")) == 1


@pytest.mark.requirement("MEM-02")
async def test_read_requires_scope(
    database: Database,
    cipher: MemoryCipher,
    clock: FakeClock,
    make_principal: PrincipalFactory,
) -> None:
    async with database.sessions() as db:
        reader = MemoryReadService(db, cipher, ScopeOnlyGuard(), clock)
        with pytest.raises(IdentityDeniedError):
            await reader.recall(make_principal(scopes=("memory:write",)), "cliente-1")


@pytest.mark.requirement("MEM-04")
async def test_expired_memories_are_not_returned(
    database: Database,
    memory_settings: Settings,
    cipher: MemoryCipher,
    clock: FakeClock,
    make_principal: PrincipalFactory,
) -> None:
    async with database.sessions() as db:
        writer = MemoryWriteService(db, memory_settings, cipher, ScopeOnlyGuard(), clock=clock)
        await writer.write(make_principal(), make_request("corto", ttl_days=1))
        await writer.write(make_principal(), make_request("largo", ttl_days=10))
        reader = MemoryReadService(db, cipher, ScopeOnlyGuard(), clock)
        assert len(await reader.recall(make_principal(), "cliente-1")) == 2
        clock.advance(2 * 86400)
        items = await reader.recall(make_principal(), "cliente-1")
    assert [item.content for item in items] == ["largo"]


@pytest.mark.requirement("MEM-04")
async def test_filter_by_kind_and_limit(
    database: Database,
    memory_settings: Settings,
    cipher: MemoryCipher,
    clock: FakeClock,
    make_principal: PrincipalFactory,
) -> None:
    async with database.sessions() as db:
        writer = MemoryWriteService(db, memory_settings, cipher, ScopeOnlyGuard(), clock=clock)
        await writer.write(make_principal(), make_request("uno", kind=MemoryKind.FACT))
        clock.advance(60)
        await writer.write(make_principal(), make_request("dos", kind=MemoryKind.EVENT))
        clock.advance(60)
        await writer.write(make_principal(), make_request("tres", kind=MemoryKind.EVENT))
        reader = MemoryReadService(db, cipher, ScopeOnlyGuard(), clock)
        events = await reader.recall(make_principal(), "cliente-1", kind=MemoryKind.EVENT)
        newest = await reader.recall(make_principal(), "cliente-1", limit=1)
    assert [item.content for item in events] == ["tres", "dos"]
    assert [item.content for item in newest] == ["tres"]
