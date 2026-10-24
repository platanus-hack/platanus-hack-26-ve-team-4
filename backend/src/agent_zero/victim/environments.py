import asyncio
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import Table, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.agent_gateway.business_policy import CallContext
from agent_zero.config import Settings
from agent_zero.memory_bank.models import MemoryRecord
from agent_zero.shared.database import AppBase, Database, acquire_write_lock, ensure_database
from agent_zero.victim.environment_state import reset_store, seed_customer, snapshot_store
from agent_zero.victim.fixtures import SYNTHETIC_CUSTOMER_IDS
from agent_zero.victim.store_models import StoreBase, StoreOperation, StoreOrder

ENVIRONMENTS = ("protected", "honeypot")

_transaction: ContextVar[tuple[str, AsyncSession] | None] = ContextVar(
    "store_transaction", default=None
)


@dataclass
class Environment:
    database: Database
    name: str
    key: str
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def initialize(self) -> None:
        async with self.database.engine.begin() as connection:
            await connection.run_sync(StoreBase.metadata.create_all)
            table = MemoryRecord.__table__
            if isinstance(table, Table):
                await connection.run_sync(AppBase.metadata.create_all, tables=[table])
        for customer_id in SYNTHETIC_CUSTOMER_IDS:
            await self.ensure_customer(customer_id)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        active = _transaction.get()
        if active is not None and active[0] == self.key:
            yield active[1]
        else:
            async with self.database.sessions() as db:
                yield db

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        """Serialize authorization and effects across workers, processes and retries."""
        async with self.lock, self.database.sessions() as db:
            await acquire_write_lock(db)
            token = _transaction.set((self.key, db))
            try:
                yield
            finally:
                _transaction.reset(token)
                if db.in_transaction():
                    await db.rollback()

    async def ensure_customer(self, customer_id: str) -> None:
        async with self.transaction(), self.session() as db:
            await seed_customer(db, self.name, customer_id)
            await db.commit()

    async def order(self, order_id: str) -> dict[str, Any] | None:
        async with self.session() as db:
            row = await db.get(StoreOrder, order_id)
            return dict(row.data) | {"refunded": row.refunded_cents / 100} if row else None

    async def orders(self) -> list[dict[str, Any]]:
        async with self.session() as db:
            return [dict(row.data) for row in await db.scalars(select(StoreOrder))]

    async def was_completed(self, operation_id: str) -> bool:
        async with self.session() as db:
            return await db.get(StoreOperation, operation_id) is not None


class Environments:
    def __init__(self, settings: Settings) -> None:
        self._urls = {name: settings.environment_database_url(name) for name in ENVIRONMENTS}
        self._environments = {
            name: Environment(Database(url), name, name) for name, url in self._urls.items()
        }

    async def initialize(self) -> None:
        for url in self._urls.values():
            await ensure_database(url)
        for environment in self._environments.values():
            await environment.initialize()

    async def ensure_customer(self, customer_id: str) -> None:
        for name in ("protected", "honeypot"):
            await self.get(name).ensure_customer(customer_id)

    def for_context(self, context: CallContext) -> Environment:
        key = context.environment_id or context.environment
        environment = self._environments.get(key)
        if environment is None or environment.name != context.environment:
            raise ValueError("Entorno de ejecución inválido.")
        return environment

    def get(self, name: str) -> Environment:
        return self._environments[name]

    async def snapshot(self) -> dict[str, dict[str, list[dict[str, Any]]]]:
        result: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for name in ("protected", "honeypot"):
            environment = self.get(name)
            async with environment.transaction(), environment.session() as db:
                result[name] = await snapshot_store(db)
        return result

    async def reset(self) -> None:
        for name in ("protected", "honeypot"):
            environment = self.get(name)
            async with environment.transaction(), environment.session() as db:
                await reset_store(db, name)
                await db.commit()

    @asynccontextmanager
    async def validation(self) -> AsyncIterator[Environment]:
        key = f"validation-{secrets.token_hex(8)}"
        environment = Environment(Database("sqlite+aiosqlite://"), "validation", key)
        self._environments[key] = environment
        try:
            await environment.initialize()
            yield environment
        finally:
            self._environments.pop(key, None)
            await environment.database.dispose()

    async def dispose(self) -> None:
        for environment in self._environments.values():
            await environment.database.dispose()
