from typing import Any

from sqlalchemy import select

from agent_zero.fleet.fleet_builder import Fleet
from agent_zero.prober.campaign_handler import CAMPAIGN_HANDLER
from agent_zero.prober.campaign_models import Campaign
from agent_zero.runtime.run_enqueue_service import RunEnqueueService
from agent_zero.runtime.schemas import RunCreate
from agent_zero.shared.ids import new_id
from agent_zero.victim.arena_manifest import ARENA_VERSION


def campaign_view(row: Campaign) -> dict[str, Any]:
    return {
        "id": row.id,
        "status": row.status,
        "max_attempts": row.max_attempts,
        "attempt_ids": row.attempt_ids,
        "created_at": row.created_at.isoformat(),
    }


class CampaignService:
    def __init__(self, fleet: Fleet) -> None:
        self._fleet = fleet

    async def start(self, max_attempts: int) -> dict[str, Any]:
        async with self._fleet.database.sessions() as db:
            active = await db.scalar(select(Campaign).where(Campaign.status == "running"))
            if active is not None:
                raise ValueError("Ya hay una campaña en curso.")
            campaign = Campaign(
                id=new_id("campaign"),
                status="running",
                max_attempts=max_attempts,
                attempt_ids=[],
                case_hashes=[],
                created_at=self._fleet.clock(),
            )
            db.add(campaign)
            await RunEnqueueService(db, self._fleet.handlers).enqueue(
                RunCreate(
                    agent_id="prober",
                    agent_version=ARENA_VERSION,
                    handler=CAMPAIGN_HANDLER,
                    input={"campaign_id": campaign.id},
                    idempotency_key=f"campaign:{campaign.id}",
                ),
                commit=False,
            )
            await db.commit()
            return campaign_view(campaign)

    async def stop(self, campaign_id: str) -> dict[str, Any]:
        async with self._fleet.database.sessions() as db:
            campaign = await db.get(Campaign, campaign_id)
            if campaign is None:
                raise ValueError("Campaña no encontrada.")
            campaign.status = "stopped"
            await db.commit()
            return campaign_view(campaign)

    async def all(self) -> list[dict[str, Any]]:
        async with self._fleet.database.sessions() as db:
            return [
                campaign_view(row)
                for row in await db.scalars(select(Campaign).order_by(Campaign.created_at))
            ]
