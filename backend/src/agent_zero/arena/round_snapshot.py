import hashlib
import json
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.arena.round_models import RoundMetadata
from agent_zero.events.models import EventRecord
from agent_zero.fleet.fleet_builder import Fleet
from agent_zero.shared.database import AppBase
from agent_zero.victim.environments import Environments

# Registry, revocations, platform memory and unrelated runs belong to the fleet.
ROUND_TABLES = frozenset(
    {
        "attempts",
        "attempt_links",
        "sessions",
        "findings",
        "finding_explanations",
        "policy_versions",
        "patch_explanations",
        "policy_pointer",
        "evaluations",
        "evaluation_executions",
        "campaigns",
        "campaign_plans",
        "campaign_cases",
        "arena_state",
    }
)


def snapshot_hash(snapshot: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


async def round_snapshot(
    db: AsyncSession, fleet: Fleet, environments: Environments, metadata: RoundMetadata
) -> dict[str, Any]:
    tables: dict[str, list[dict[str, Any]]] = {}
    for name in sorted(ROUND_TABLES | {"runs", "run_events", "run_leases"}):
        table = AppBase.metadata.tables.get(name)
        if table is not None:
            tables[name] = [dict(row) for row in (await db.execute(select(table))).mappings()]
    tables[EventRecord.__tablename__] = [
        dict(row)
        for row in (
            await db.execute(
                select(EventRecord.__table__).where(EventRecord.id >= metadata.first_event_id)
            )
        ).mappings()
    ]
    snapshot: dict[str, Any] = {
        "schema_version": 1,
        "round_id": metadata.round_id,
        "started_at": metadata.started_at,
        "application": tables,
        "environments": await environments.snapshot(),
        "audit": [entry.model_dump(mode="json") for entry in fleet.audit.entries()],
    }
    encoded: dict[str, Any] = jsonable_encoder(snapshot)
    return encoded
