from sqlalchemy import Table

from agent_zero.identity.models import RevokedAgent, RevokedCredential
from agent_zero.memory_bank.models import MemoryRecord
from agent_zero.registry.models import AgentVersion
from agent_zero.runtime.models import Run, RunEvent, RunLease
from agent_zero.shared.database import AppBase, Database

FLEET_TABLES = (
    AgentVersion,
    MemoryRecord,
    RevokedAgent,
    RevokedCredential,
    Run,
    RunEvent,
    RunLease,
)


async def create_fleet_schema(database: Database) -> None:
    tables = [model.__table__ for model in FLEET_TABLES if isinstance(model.__table__, Table)]
    async with database.engine.begin() as connection:
        await connection.run_sync(AppBase.metadata.create_all, tables=tables)
