from typing import Any

from fastapi import APIRouter, HTTPException

from agent_zero.arena.dependencies import Core

router = APIRouter(prefix="/api/arena", tags=["arena"])
MISSING = "No hay repetición para esa política."


@router.get("/replay/{version}")
async def replay(version: int, core: Core) -> dict[str, Any]:
    try:
        policy = await core.policies.get(version)
    except (KeyError, ValueError):
        raise HTTPException(status_code=404, detail=MISSING) from None
    validation = policy["validation"]
    stored = validation.get("replay")
    if validation.get("passed") is not True or not isinstance(stored, dict):
        raise HTTPException(status_code=404, detail=MISSING)
    return {"version": version, **stored}
