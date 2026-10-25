from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import or_, select

from agent_zero.arena.audit_view import Tables, chat_detail, chat_index, plain
from agent_zero.arena.dependencies import Core
from agent_zero.arena.round_models import RoundMetadata
from agent_zero.attempts.models import Attempt, AttemptLink
from agent_zero.events.models import EventRecord, EventType
from agent_zero.prober.campaign_models import CampaignCaseRecord
from agent_zero.registry.dependencies import OperatorOnly
from agent_zero.sessions.models import ArenaSession

router = APIRouter(prefix="/api/operator/audit", tags=["operator"], dependencies=[OperatorOnly])

RoundQuery = Annotated[str | None, Query(alias="round", max_length=40)]


async def current_tables(core: Core, session_id: str | None = None) -> Tables:
    """Filas de la ronda en curso; con `session_id`, solo las de esa sesión."""
    async with core.fleet.database.sessions() as db:
        metadata = await db.get(RoundMetadata, 1)
        first_event = metadata.first_event_id if metadata else 0
        sessions = select(ArenaSession)
        attempts = select(Attempt)
        if session_id is not None:
            sessions = sessions.where(ArenaSession.id == session_id)
            attempts = attempts.where(Attempt.session_id == session_id)
        attempt_rows = list(await db.scalars(attempts))
        ids = [row.id for row in attempt_rows]
        events = select(EventRecord).where(EventRecord.id >= first_event)
        if session_id is None:
            events = events.where(EventRecord.type == EventType.ROUTE_CHANGED)
        else:
            events = events.where(
                or_(EventRecord.attempt_id.in_(ids), EventRecord.session_id == session_id)
            )
        links = select(AttemptLink)
        if session_id is not None:
            links = links.where(AttemptLink.attempt_id.in_(ids))
        cases: list[dict[str, Any]] = []
        if session_id is not None:
            cases_query = select(CampaignCaseRecord).where(CampaignCaseRecord.attempt_id.in_(ids))
            cases = plain(_columns(row) for row in await db.scalars(cases_query))
        return {
            "sessions": plain(_columns(row) for row in await db.scalars(sessions)),
            "attempts": plain(_columns(row) for row in attempt_rows),
            "attempt_links": plain(_columns(row) for row in await db.scalars(links)),
            "product_events": plain(_columns(row) for row in await db.scalars(events)),
            "campaign_cases": cases,
        }


def _columns(row: Any) -> dict[str, Any]:
    return {column.key: getattr(row, column.key) for column in row.__table__.columns}


async def round_tables(core: Core, archive_id: str | None, session_id: str | None = None) -> Tables:
    if not archive_id:
        return await current_tables(core, session_id)
    try:
        archive = await core.rounds.archive(archive_id)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    if archive is None:
        raise HTTPException(404, "Ronda archivada no encontrada.")
    application: Tables = archive["snapshot"].get("application", {})
    return application


@router.get("/rounds")
async def rounds(core: Core) -> list[dict[str, Any]]:
    """La ronda en curso y las archivadas, de la más reciente a la más antigua."""
    async with core.fleet.database.sessions() as db:
        metadata = await db.get(RoundMetadata, 1)
    current = (
        [
            {
                "id": None,
                "round_id": metadata.round_id,
                "current": True,
                "started_at": metadata.started_at.isoformat(),
                "reason": "",
            }
        ]
        if metadata
        else []
    )
    archived = [
        {
            "id": row["id"],
            "round_id": row["round_id"],
            "current": False,
            "started_at": row["created_at"],
            "reason": row["reason"],
        }
        for row in await core.rounds.archives()
        if row["status"] == "completed"
    ]
    return current + archived


@router.get("/chats")
async def chats(core: Core, archive: RoundQuery = None) -> list[dict[str, Any]]:
    return chat_index(await round_tables(core, archive))


@router.get("/chats/{session_id}")
async def chat(session_id: str, core: Core, archive: RoundQuery = None) -> dict[str, Any]:
    detail = chat_detail(await round_tables(core, archive, session_id), session_id)
    if detail is None:
        raise HTTPException(404, "Chat no encontrado.")
    return detail
