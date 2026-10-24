import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import update

from agent_zero.events.event_store import EventStore
from agent_zero.events.models import EventType
from agent_zero.policies.lifecycle import transition
from agent_zero.policies.models import PolicyPointer, PolicyStatus, PolicyVersion
from agent_zero.policies.repository import PolicyRepository, content_hash, policy_view
from agent_zero.policies.validator_catalog import CONTROL_REASONS, OBJECTIVE_CONTROLS
from agent_zero.shared.clock import utc_now
from agent_zero.shared.database import Database


class PolicyService:
    def __init__(
        self, database: Database, events: EventStore, admission_lock: asyncio.Lock
    ) -> None:
        self._database = database
        self._events = events
        self._admission_lock = admission_lock

    async def initialize(self) -> None:
        async with self._database.sessions() as db:
            await PolicyRepository(db).initialize()

    async def active_version(self) -> int:
        async with self._database.sessions() as db:
            return (await PolicyRepository(db).active()).version

    async def get(self, version: int) -> dict[str, Any]:
        async with self._database.sessions() as db:
            return policy_view(await PolicyRepository(db).require(version))

    async def all(self) -> list[dict[str, Any]]:
        async with self._database.sessions() as db:
            return await PolicyRepository(db).all()

    async def propose(
        self,
        finding_id: str,
        objective_id: str,
        *,
        related: list[tuple[str, str]] | None = None,
        evidence_attempt_ids: list[str] | None = None,
    ) -> int | None:
        async with self._admission_lock, self._database.sessions() as db:
            repository = PolicyRepository(db)
            if await repository.pending() is not None:
                return None
            active = await repository.active()
            targets = [(finding_id, objective_id), *(related or [])]
            controls = {
                control for _, objective in targets for control in OBJECTIVE_CONTROLS[objective]
            }
            rules = sorted(set(active.rules) | controls)
            if rules == active.rules:
                return None
            version = await repository.next_version()
            db.add(
                PolicyVersion(
                    version=version,
                    parent_version=active.version,
                    rules=rules,
                    content_hash=content_hash(rules, active.version),
                    status=PolicyStatus.CANDIDATE,
                    finding_ids=list(dict.fromkeys(finding for finding, _ in targets)),
                    reason=" ".join(
                        dict.fromkeys(CONTROL_REASONS[objective] for _, objective in targets)
                    ),
                    validation={"evidence_attempt_ids": evidence_attempt_ids or []},
                    created_at=utc_now(),
                )
            )
            await db.commit()
        await self._events.public(
            EventType.PATCH_PROPOSED, version, version=version, finding_id=finding_id
        )
        return version

    async def start_validation(self, version: int) -> bool:
        async with self._database.sessions() as db:
            row = await PolicyRepository(db).require(version)
            if row.status is PolicyStatus.CANDIDATE:
                row.status = transition(row.status, PolicyStatus.VALIDATING)
                await db.commit()
            return row.status is PolicyStatus.VALIDATING

    async def record_validation(self, version: int, report: dict[str, Any]) -> None:
        async with self._database.sessions() as db:
            row = await PolicyRepository(db).require(version)
            if row.status is not PolicyStatus.VALIDATING:
                return
            row.validation = row.validation | report
            if not report.get("passed"):
                row.status = transition(row.status, PolicyStatus.REJECTED)
            await db.commit()
        await self._events.public(
            EventType.PATCH_VALIDATED, version, version=version, passed=bool(report.get("passed"))
        )

    async def activate(
        self,
        version: int,
        drained: Callable[[], Awaitable[bool]],
        *,
        before_activate: Callable[[], Awaitable[None]] | None = None,
    ) -> bool:
        async with self._admission_lock:
            if not await drained():
                return False
            async with self._database.sessions() as db:
                repository = PolicyRepository(db)
                row = await repository.require(version)
                if row.status is PolicyStatus.ACTIVE:
                    return True
                if row.status is not PolicyStatus.VALIDATING or not row.validation.get("passed"):
                    return False
                active = await repository.active()
                if row.parent_version != active.version:
                    row.status = transition(row.status, PolicyStatus.REJECTED)
                    row.validation = row.validation | {"passed": False, "reason": "stale_parent"}
                    await db.commit()
                    return False
                if before_activate is not None:
                    await before_activate()
                changed = await db.scalar(
                    update(PolicyPointer)
                    .where(
                        PolicyPointer.id == 1,
                        PolicyPointer.version == row.parent_version,
                    )
                    .values(version=version)
                    .returning(PolicyPointer.version)
                )
                if changed != version:
                    await db.rollback()
                    return False
                active.status = transition(active.status, PolicyStatus.SUPERSEDED)
                row.status = transition(row.status, PolicyStatus.ACTIVE)
                row.activated_at = utc_now()
                await db.commit()
        await self._events.public(
            EventType.POLICY_ACTIVATED,
            version,
            version=version,
            dedup_key=f"policy:{version}:activated",
        )
        return True

    async def finalize(self, version: int) -> None:
        await self._events.public(
            EventType.POLICY_ACTIVATED,
            version,
            version=version,
            dedup_key=f"policy:{version}:activated",
        )
        async with self._database.sessions() as db:
            row = await PolicyRepository(db).require(version)
            row.validation = row.validation | {"finalized": True}
            await db.commit()

    async def rollback(
        self, version: int, reason: str, drained: Callable[[], Awaitable[bool]]
    ) -> int:
        async with self._admission_lock:
            if not await drained():
                raise ValueError("Hay intentos en curso; vuelve a intentar al terminar.")
            async with self._database.sessions() as db:
                repository = PolicyRepository(db)
                row = await repository.active()
                if row.version != version or row.parent_version is None:
                    raise ValueError("Solo se revierte la versión activa que tiene padre.")
                parent = await repository.require(row.parent_version)
                if not parent.validation.get("passed"):
                    raise ValueError("El padre no cuenta con validación.")
                row.status = transition(row.status, PolicyStatus.ROLLED_BACK)
                # Restoring a verified snapshot does not revive it as a new candidate.
                parent.status = PolicyStatus.ACTIVE
                pointer = await db.get(PolicyPointer, 1)
                if pointer is None:
                    raise ValueError("No existe el puntero activo.")
                pointer.version = parent.version
                row.validation = row.validation | {"rollback_reason": reason}
                await db.commit()
                target = parent.version
        await self._events.public(EventType.POLICY_ROLLED_BACK, target, version=target)
        return target
