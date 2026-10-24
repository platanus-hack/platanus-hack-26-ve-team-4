from fastapi import APIRouter, HTTPException

from agent_zero.arena.dependencies import Core
from agent_zero.decoy.models import DecoySummary, RevealCard
from agent_zero.registry.dependencies import OperatorOnly
from agent_zero.sessions.dependencies import CurrentSession

router = APIRouter(tags=["decoy"])


@router.get("/api/operator/decoy", dependencies=[OperatorOnly])
async def operator_summary(core: Core) -> DecoySummary:
    return await core.decoy.summary()


@router.get("/api/decoy/reveal")
async def reveal_card(session: CurrentSession, core: Core) -> RevealCard:
    if not await core.attempts.revealed():
        raise HTTPException(403, "La revelación aún no ocurrió.")
    card = await core.decoy.card_for(session.id)
    if card is None:
        raise HTTPException(404, "Tu sesión no pasó por el señuelo.")
    return card
