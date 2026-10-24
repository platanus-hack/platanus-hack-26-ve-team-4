import pytest

from agent_zero.config import Settings
from agent_zero.identity.errors import IdentityDeniedError
from agent_zero.memory_bank.memory_cipher import MemoryCipher
from agent_zero.memory_bank.memory_forget_service import MemoryForgetService
from agent_zero.memory_bank.memory_read_service import MemoryReadService
from agent_zero.memory_bank.memory_write_service import MemoryWriteService
from agent_zero.shared.database import Database
from tests.identity.conftest import FakeClock
from tests.memory_bank.conftest import PrincipalFactory, make_request


@pytest.mark.requirement("MEM-04")
async def test_forget_subject_removes_all_and_only_that_subject(
    database: Database,
    memory_settings: Settings,
    cipher: MemoryCipher,
    clock: FakeClock,
    make_principal: PrincipalFactory,
) -> None:
    async with database.sessions() as db:
        writer = MemoryWriteService(db, memory_settings, cipher, clock=clock)
        await writer.write(make_principal(), make_request("a"))
        await writer.write(make_principal(), make_request("b"))
        await writer.write(make_principal(), make_request("c", subject_id="cliente-2"))
        deleted = await MemoryForgetService(db, clock).forget_subject(make_principal(), "cliente-1")
        reader = MemoryReadService(db, cipher, clock)
        assert deleted == 2
        assert await reader.recall(make_principal(), "cliente-1") == []
        assert len(await reader.recall(make_principal(), "cliente-2")) == 1


@pytest.mark.requirement("MEM-02", "MEM-04")
async def test_forget_does_not_touch_other_agents_and_needs_scope(
    database: Database,
    memory_settings: Settings,
    cipher: MemoryCipher,
    clock: FakeClock,
    make_principal: PrincipalFactory,
) -> None:
    other = make_principal(agent_id="agent-otro")
    async with database.sessions() as db:
        await MemoryWriteService(db, memory_settings, cipher, clock=clock).write(
            other, make_request()
        )
        forget = MemoryForgetService(db, clock)
        assert await forget.forget_subject(make_principal(), "cliente-1") == 0
        with pytest.raises(IdentityDeniedError):
            await forget.forget_subject(make_principal(scopes=("memory:read",)), "cliente-1")
        assert len(await MemoryReadService(db, cipher, clock).recall(other, "cliente-1")) == 1


@pytest.mark.requirement("MEM-04")
async def test_purge_expired_deletes_only_expired(
    database: Database,
    memory_settings: Settings,
    cipher: MemoryCipher,
    clock: FakeClock,
    make_principal: PrincipalFactory,
) -> None:
    async with database.sessions() as db:
        writer = MemoryWriteService(db, memory_settings, cipher, clock=clock)
        await writer.write(make_principal(), make_request("corto", ttl_days=1))
        await writer.write(make_principal(), make_request("largo", ttl_days=10))
        clock.advance(2 * 86400)
        assert await MemoryForgetService(db, clock).purge_expired() == 1
        assert (
            len(await MemoryReadService(db, cipher, clock).recall(make_principal(), "cliente-1"))
            == 1
        )
