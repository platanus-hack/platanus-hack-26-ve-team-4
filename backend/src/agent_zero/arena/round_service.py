from typing import Any

from sqlalchemy import delete, select, update

from agent_zero.arena.models import ArenaState
from agent_zero.arena.round_models import RoundArchive, RoundMetadata
from agent_zero.arena.round_snapshot import (
    ROUND_TABLES,
    round_snapshot,
    snapshot_hash,
)
from agent_zero.arena.round_state import ARENA_HANDLERS
from agent_zero.arena.transactions import serialize_write
from agent_zero.attempts.repository import AttemptRepository
from agent_zero.events.event_store import EventStore
from agent_zero.events.models import EventRecord, EventType, Visibility
from agent_zero.events.schemas import EventDraft
from agent_zero.fleet.fleet_builder import Fleet
from agent_zero.policies.repository import PolicyRepository
from agent_zero.runtime.models import TERMINAL_STATUSES, Run, RunEvent, RunLease
from agent_zero.shared.database import AppBase
from agent_zero.shared.ids import new_id
from agent_zero.victim.environments import Environments


class RoundService:
    def __init__(self, fleet: Fleet, events: EventStore, environments: Environments) -> None:
        self._fleet = fleet
        self._events = events
        self._environments = environments

    async def initialize(self) -> None:
        async with self._fleet.database.sessions() as db:
            await serialize_write(db)
            if await db.get(RoundMetadata, 1) is None:
                db.add(
                    RoundMetadata(id=1, round_id=new_id("round"), started_at=self._fleet.clock())
                )
                await db.commit()
        await self.recover()

    async def recover(self) -> str | None:
        async with self._fleet.database.sessions() as db:
            archive = await db.scalar(
                select(RoundArchive).where(RoundArchive.status == "resetting")
            )
        if archive is None:
            return None
        await self._complete(archive)
        return archive.id

    async def reset(self, reason: str) -> str:
        """Caller stops local workers and holds admission_lock for this operation."""
        recovered = await self.recover()
        if recovered is not None:
            return recovered
        async with self._fleet.database.sessions() as db:
            await serialize_write(db)
            if await AttemptRepository(db).in_flight():
                raise ValueError("Espera a que terminen los intentos antes de reiniciar.")
            active_run = await db.scalar(
                select(Run.run_id)
                .where(Run.handler.in_(ARENA_HANDLERS), ~Run.status.in_(TERMINAL_STATUSES))
                .limit(1)
            )
            if active_run is not None:
                raise ValueError("Hay campañas o validaciones pendientes; detén o drena la ronda.")
            state = await db.get(ArenaState, 1)
            metadata = await db.get(RoundMetadata, 1)
            if state is None or metadata is None:
                raise ValueError("Ronda no inicializada.")
            snapshot = await round_snapshot(db, self._fleet, self._environments, metadata)
            archive = RoundArchive(
                id=new_id("archive"),
                round_id=metadata.round_id,
                next_round_id=new_id("round"),
                reason=self._fleet.armor.redact_pii(reason),
                status="resetting",
                snapshot=snapshot,
                content_hash=snapshot_hash(snapshot),
                created_at=self._fleet.clock(),
            )
            db.add(archive)
            state.accepting = False
            await db.commit()
        await self._complete(archive)
        return archive.id

    async def _complete(self, archive: RoundArchive) -> None:
        if snapshot_hash(archive.snapshot) != archive.content_hash:
            raise ValueError("El archivo de la ronda fue alterado; no se reiniciarán los datos.")
        # A crash after either environment is reset is safe: resetting is durable,
        # entries remain closed, and startup repeats these idempotent operations.
        async with self._fleet.database.sessions() as db:
            await serialize_write(db)
            stored = await db.get(RoundArchive, archive.id)
            if stored is None or stored.status == "completed":
                return
            await self._environments.reset()
            run_ids = select(Run.run_id).where(Run.handler.in_(ARENA_HANDLERS))
            await db.execute(delete(RunEvent).where(RunEvent.run_id.in_(run_ids)))
            await db.execute(delete(RunLease).where(RunLease.run_id.in_(run_ids)))
            await db.execute(delete(Run).where(Run.handler.in_(ARENA_HANDLERS)))
            for table in reversed(AppBase.metadata.sorted_tables):
                if table.name in ROUND_TABLES:
                    await db.execute(delete(table))
            # Event IDs remain monotonic across rounds. Drop old dedup reservations
            # so policy numbers can start at zero without colliding with history.
            await db.execute(update(EventRecord).values(dedup_key=None))
            await PolicyRepository(db).initialize(commit=False)
            db.add(ArenaState(id=1, accepting=True, revealed=False))
            metadata = await db.get(RoundMetadata, 1)
            if metadata is None:
                raise ValueError("Faltan los metadatos de la ronda.")
            metadata.round_id = stored.next_round_id
            metadata.started_at = self._fleet.clock()
            event = await self._events.stage(
                db,
                EventDraft(
                    type=EventType.ROUND_STARTED,
                    visibility=Visibility.PUBLIC,
                    policy_version=0,
                    data={"round_id": metadata.round_id},
                ),
                dedup_key=f"{metadata.round_id}:started",
            )
            metadata.first_event_id = event.id
            stored.status = "completed"
            stored.completed_at = self._fleet.clock()
            await db.commit()
        await self._events.dispatch_pending()

    async def archives(self) -> list[dict[str, Any]]:
        async with self._fleet.database.sessions() as db:
            rows = await db.scalars(select(RoundArchive).order_by(RoundArchive.created_at.desc()))
            return [
                {
                    "id": row.id,
                    "round_id": row.round_id,
                    "reason": row.reason,
                    "status": row.status,
                    "content_hash": row.content_hash,
                    "created_at": row.created_at.isoformat(),
                    "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                }
                for row in rows
            ]

    async def archive(self, archive_id: str) -> dict[str, Any] | None:
        async with self._fleet.database.sessions() as db:
            row = await db.get(RoundArchive, archive_id)
            if row is None:
                return None
            if snapshot_hash(row.snapshot) != row.content_hash:
                raise ValueError("El archivo de la ronda fue alterado.")
            return {"id": row.id, "content_hash": row.content_hash, "snapshot": row.snapshot}
