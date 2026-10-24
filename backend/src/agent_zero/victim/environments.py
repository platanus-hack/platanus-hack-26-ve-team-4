import asyncio
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import Table, select

from agent_zero.agent_gateway.business_policy import CallContext
from agent_zero.memory_bank.models import MemoryRecord
from agent_zero.shared.database import AppBase, Database
from agent_zero.victim.fixtures import ORDERS
from agent_zero.victim.store_models import StoreBase, StoreOperation, StoreOrder


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
        async with self.database.sessions() as db:
            if await db.scalar(select(StoreOrder.id).limit(1)) is not None:
                return
            prefix = "AZH" if self.name == "honeypot" else "AZP"
            for order in ORDERS.values():
                data = order.model_dump(mode="json")
                data["canary"] = f"{prefix}_{secrets.token_hex(8)}_{order.order_id}"
                if self.name == "honeypot":
                    data["items"] = ["producto de demostración"]
                db.add(StoreOrder(id=order.order_id, data=data, refunded_cents=0))
            await db.commit()

    async def order(self, order_id: str) -> dict[str, Any] | None:
        async with self.database.sessions() as db:
            row = await db.get(StoreOrder, order_id)
            return dict(row.data) | {"refunded": row.refunded_cents / 100} if row else None

    async def orders(self) -> list[dict[str, Any]]:
        async with self.database.sessions() as db:
            return [dict(row.data) for row in await db.scalars(select(StoreOrder))]

    async def was_completed(self, operation_id: str) -> bool:
        async with self.database.sessions() as db:
            return await db.get(StoreOperation, operation_id) is not None


class Environments:
    def __init__(self, data_dir: Path) -> None:
        self._environments = {
            name: Environment(
                Database(f"sqlite+aiosqlite:///{data_dir / (name + '.db')}"), name, name
            )
            for name in ("protected", "honeypot")
        }

    async def initialize(self) -> None:
        for environment in self._environments.values():
            await environment.initialize()

    def for_context(self, context: CallContext) -> Environment:
        key = context.environment_id or context.environment
        environment = self._environments.get(key)
        if environment is None or environment.name != context.environment:
            raise ValueError("Entorno de ejecución inválido.")
        return environment

    def get(self, name: str) -> Environment:
        return self._environments[name]

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
