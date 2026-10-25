"""Conversación del chat: un intento puede continuar a otro de la misma sesión.

El historial lo arma el servidor desde sus propios registros; el cliente solo dice a qué intento
responde. Los turnos previos entran al modelo como texto: sus herramientas no se repiten.
"""

import re
from collections.abc import Iterable

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.attempts.models import Attempt, AttemptLink, AttemptStatus

CANARY = re.compile(r"AZ[PH]_[a-f0-9]+_[A-Z]-\d+")

# Intentos previos que el modelo puede ver; al llegar al tope se empieza otra conversación.
MAX_PREVIOUS = 30
TERMINAL = {AttemptStatus.EVALUATED, AttemptStatus.INCONCLUSIVE}
Turn = tuple[list[str], str]


def public_reply(text: str) -> str:
    """La respuesta tal como la vio el participante: sin los canarios internos."""
    return CANARY.sub("[referencia]", text)


async def chain(db: AsyncSession, attempt_id: str) -> list[Attempt]:
    """El intento y sus anteriores, del más antiguo al más reciente."""
    found: list[Attempt] = []
    current: str | None = attempt_id
    while current is not None and len(found) <= MAX_PREVIOUS:
        attempt = await db.get(Attempt, current)
        if attempt is None:
            break
        found.append(attempt)
        link = await db.get(AttemptLink, current)
        current = None if link is None else link.previous_attempt_id
    return list(reversed(found))


async def check_continuation(db: AsyncSession, session_id: str, previous_id: str) -> None:
    previous = await db.get(Attempt, previous_id)
    if previous is None or previous.session_id != session_id:
        raise HTTPException(404, "La conversación anterior no existe en esta sesión.")
    if previous.status not in TERMINAL:
        raise HTTPException(409, "Espera la respuesta anterior antes de continuar.")
    if len(await chain(db, previous_id)) >= MAX_PREVIOUS:
        raise HTTPException(409, "La conversación llegó a su largo máximo; inicia una nueva.")


async def previous_turns(db: AsyncSession, attempt_id: str) -> list[Turn]:
    link = await db.get(AttemptLink, attempt_id)
    if link is None:
        return []
    return [
        (attempt.messages, public_reply(attempt.reply))
        for attempt in await chain(db, link.previous_attempt_id)
    ]


async def links_for(db: AsyncSession, attempt_ids: Iterable[str]) -> dict[str, str]:
    ids = list(attempt_ids)
    if not ids:
        return {}
    rows = await db.scalars(select(AttemptLink).where(AttemptLink.attempt_id.in_(ids)))
    return {row.attempt_id: row.previous_attempt_id for row in rows}
