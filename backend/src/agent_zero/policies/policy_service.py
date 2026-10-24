import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import select, update

from agent_zero.analyzer.models import FindingRecord, FindingStatus
from agent_zero.arena.transactions import serialize_write
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
            await serialize_write(db)
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
            await serialize_write(db)
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
            await self._events.stage_public(
                db,
                EventType.PATCH_PROPOSED,
                version,
                version=version,
                finding_id=finding_id,
                dedup_key=f"policy:{version}:proposed",
            )
            await db.commit()
        await self._events.dispatch_pending()
        return version

    async def start_validation(self, version: int) -> bool:
        async with self._database.sessions() as db:
            await serialize_write(db)
            row = await PolicyRepository(db).require(version)
            if row.status is PolicyStatus.CANDIDATE:
                row.status = transition(row.status, PolicyStatus.VALIDATING)
                await db.commit()
            return row.status is PolicyStatus.VALIDATING and "passed" not in row.validation

    async def record_validation(self, version: int, report: dict[str, Any]) -> None:
        async with self._database.sessions() as db:
            await serialize_write(db)
            row = await PolicyRepository(db).require(version)
            if row.status is not PolicyStatus.VALIDATING or "passed" in row.validation:
                return
            row.validation = row.validation | report
            if report.get("passed") is not True:
                row.status = transition(row.status, PolicyStatus.REJECTED)
            await self._events.stage_public(
                db,
                EventType.PATCH_VALIDATED,
                version,
                version=version,
                passed=report.get("passed") is True,
                dedup_key=f"policy:{version}:validated",
            )
            await db.commit()
        await self._events.dispatch_pending()

    async def activate(
        self,
        version: int,
        drained: Callable[[], Awaitable[bool]],
        *,
        before_activate: Callable[[], Awaitable[None]] | None = None,
    ) -> bool:
        async with self._admission_lock, self._database.sessions() as db:
            await serialize_write(db)
            if not await drained():
                return False
            repository = PolicyRepository(db)
            row = await repository.require(version)
            if row.status is PolicyStatus.ACTIVE:
                return (await repository.active()).version == version
            if (
                row.status is not PolicyStatus.VALIDATING
                or row.validation.get("passed") is not True
            ):
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
            await self._events.stage_public(
                db,
                EventType.POLICY_ACTIVATED,
                version,
                version=version,
                dedup_key=f"policy:{version}:activated",
            )
            await db.commit()
        await self._events.dispatch_pending()
        return True

    async def finalize(self, version: int) -> None:
        async with self._database.sessions() as db:
            await serialize_write(db)
            row = await PolicyRepository(db).require(version)
            if row.status is not PolicyStatus.ACTIVE:
                return
            await self._events.stage_public(
                db,
                EventType.POLICY_ACTIVATED,
                version,
                version=version,
                dedup_key=f"policy:{version}:activated",
            )
            row.validation = row.validation | {"finalized": True}
            await db.commit()
        await self._events.dispatch_pending()

    async def rollback(
        self, version: int, reason: str, drained: Callable[[], Awaitable[bool]]
    ) -> int:
        async with self._admission_lock, self._database.sessions() as db:
            await serialize_write(db)
            if not await drained():
                raise ValueError("Hay intentos en curso; vuelve a intentar al terminar.")
            repository = PolicyRepository(db)
            row = await repository.active()
            if row.version != version or row.parent_version is None:
                raise ValueError("Solo se revierte la versión activa que tiene padre.")
            parent = await repository.require(row.parent_version)
            if parent.validation.get("passed") is not True:
                raise ValueError("El padre no cuenta con validación.")
            row.status = transition(row.status, PolicyStatus.ROLLED_BACK)
            # Restoring a verified snapshot does not revive it as a new candidate.
            parent.status = PolicyStatus.ACTIVE
            pointer = await db.get(PolicyPointer, 1)
            if pointer is None:
                raise ValueError("No existe el puntero activo.")
            pointer.version = parent.version
            row.validation = row.validation | {"rollback_reason": reason}
            for finding in await db.scalars(
                select(FindingRecord).where(FindingRecord.status == FindingStatus.MITIGATED)
            ):
                if not set(finding.missing_control.split("+")) <= set(parent.rules):
                    finding.status = FindingStatus.REOPENED
                    finding.updated_at = utc_now()
            target = parent.version
            await self._events.stage_public(
                db,
                EventType.POLICY_ROLLED_BACK,
                target,
                version=target,
                dedup_key=f"policy:{version}:rolled_back",
            )
            await db.commit()
        await self._events.dispatch_pending()
        return target
