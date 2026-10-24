import pytest

from agent_zero.config import Settings
from agent_zero.memory_bank.memory_cipher import MemoryCipher
from agent_zero.memory_bank.memory_erasure_service import MemoryErasureService
from agent_zero.memory_bank.memory_read_service import MemoryReadService
from agent_zero.memory_bank.memory_write_service import MemoryWriteService
from agent_zero.shared.database import Database
from tests.identity.conftest import FakeClock
from tests.memory_bank.conftest import PrincipalFactory, make_request
from tests.memory_bank.support import ScopeOnlyGuard


@pytest.mark.requirement("MEM-04")
async def test_erasing_a_subject_removes_it_for_every_agent(
    database: Database,
    memory_settings: Settings,
    cipher: MemoryCipher,
    clock: FakeClock,
    make_principal: PrincipalFactory,
) -> None:
    soporte = make_principal()
    finanzas = make_principal(agent_id="agent-finanzas")
    async with database.sessions() as db:
        writer = MemoryWriteService(db, memory_settings, cipher, ScopeOnlyGuard(), clock=clock)
        await writer.write(soporte, make_request("a"))
        await writer.write(finanzas, make_request("b"))
        await writer.write(finanzas, make_request("c", subject_id="cliente-2"))
        assert await MemoryErasureService(db).erase_subject("cliente-1") == 2
        reader = MemoryReadService(db, cipher, ScopeOnlyGuard(), clock)
        assert await reader.recall(soporte, "cliente-1") == []
        assert await reader.recall(finanzas, "cliente-1") == []
        assert len(await reader.recall(finanzas, "cliente-2")) == 1
