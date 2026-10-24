from typing import Any

from agent_zero.arena.transactions import serialize_write
from agent_zero.guard.repository import active_policy, findings, policies, policy
from agent_zero.guard.views import finding_view, policy_view
from agent_zero.shared.database import Database


class PolicyStateError(ValueError):
    pass


class GuardAdminService:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def policies(self, contract_id: str) -> list[dict[str, Any]]:
        async with self._database.sessions() as db:
            return [policy_view(row) for row in await policies(db, contract_id)]

    async def findings(self, contract_id: str) -> list[dict[str, Any]]:
        async with self._database.sessions() as db:
            return [finding_view(row) for row in await findings(db, contract_id)]

    async def activate(self, contract_id: str, version: int) -> dict[str, Any]:
        async with self._database.sessions() as db:
            await serialize_write(db)
            target = await policy(db, contract_id, version)
            if target is None or target.status != "proposed":
                raise PolicyStateError("Solo se activa una versión propuesta.")
            current = await active_policy(db, contract_id)
            if current is not None:
                current.status = "superseded"
            target.status = "active"
            view = policy_view(target)
            await db.commit()
        return view

    async def rollback(self, contract_id: str, version: int) -> dict[str, Any] | None:
        async with self._database.sessions() as db:
            await serialize_write(db)
            target = await policy(db, contract_id, version)
            if target is None or target.status != "active":
                raise PolicyStateError("Solo se revierte la versión activa.")
            target.status = "rolled_back"
            parent = await policy(db, contract_id, target.parent_version)
            if parent is not None:
                parent.status = "active"
            view = policy_view(parent) if parent else None
            await db.commit()
        return view
