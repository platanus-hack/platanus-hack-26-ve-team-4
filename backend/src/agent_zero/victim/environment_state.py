import secrets
from datetime import datetime
from typing import Any

from sqlalchemy import Table, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.memory_bank.models import MemoryRecord
from agent_zero.victim.fixtures import SYNTHETIC_CUSTOMER_IDS, orders_for_customer
from agent_zero.victim.store_models import StoreBase, StoreOrder


async def seed_customer(db: AsyncSession, environment_name: str, customer_id: str) -> None:
    prefix = "AZH" if environment_name == "honeypot" else "AZP"
    for order in orders_for_customer(customer_id):
        if await db.get(StoreOrder, order.order_id) is not None:
            continue
        data = order.model_dump(mode="json")
        data["canary"] = f"{prefix}_{secrets.token_hex(8)}_{order.order_id}"
        if environment_name == "honeypot":
            data["items"] = ["producto de demostración"]
        db.add(StoreOrder(id=order.order_id, data=data, refunded_cents=0))


def _tables() -> list[Table]:
    memory_table = MemoryRecord.__table__
    assert isinstance(memory_table, Table)
    return [*StoreBase.metadata.sorted_tables, memory_table]


async def snapshot_store(db: AsyncSession) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for table in _tables():
        rows = (await db.execute(select(table))).mappings()
        result[table.name] = [
            {
                key: value.isoformat() if isinstance(value, datetime) else value
                for key, value in row.items()
            }
            for row in rows
        ]
    return result


async def reset_store(db: AsyncSession, environment_name: str) -> None:
    for table in reversed(_tables()):
        await db.execute(delete(table))
    for customer_id in SYNTHETIC_CUSTOMER_IDS:
        await seed_customer(db, environment_name, customer_id)
