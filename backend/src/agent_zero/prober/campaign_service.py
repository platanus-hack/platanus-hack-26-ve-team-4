from typing import Any

from sqlalchemy import select

from agent_zero.arena.models import ArenaState
from agent_zero.arena.transactions import serialize_write
from agent_zero.fleet.fleet_builder import Fleet
from agent_zero.prober.campaign_handler import CAMPAIGN_HANDLER
from agent_zero.prober.campaign_models import Campaign, CampaignCaseRecord, CampaignPlan
from agent_zero.runtime.run_enqueue_service import RunEnqueueService
from agent_zero.runtime.schemas import RunCreate
from agent_zero.shared.ids import new_id
from agent_zero.victim.arena_manifest import ARENA_VERSION


def campaign_view(
    row: Campaign,
    plan: CampaignPlan | None = None,
    cases: list[CampaignCaseRecord] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": row.id,
        "status": row.status,
        "max_attempts": row.max_attempts,
        "attempt_ids": row.attempt_ids,
        "created_at": row.created_at.isoformat(),
        "generation": plan.generation if plan else "templates",
        "generation_calls": plan.generation_calls if plan else 0,
        "max_mutations": plan.max_mutations if plan else 0,
        "stop_reason": plan.stop_reason if plan else "",
        "cases": [
            {
                "index": case.index,
                "status": case.status,
                "attempt_id": case.attempt_id,
                "digest": case.digest,
                "error": case.error,
                "case": case.case_json,
            }
            for case in cases or []
        ],
    }
    return result


class CampaignService:
    def __init__(self, fleet: Fleet) -> None:
        self._fleet = fleet

    async def start(
        self, max_attempts: int, generation: str = "templates", max_mutations: int = 30
    ) -> dict[str, Any]:
        if not 1 <= max_attempts <= 30 or generation not in {"templates", "llm"}:
            raise ValueError("La campaña admite de uno a treinta casos y un generador válido.")
        if not 1 <= max_mutations <= 30:
            raise ValueError("El presupuesto de mutación debe estar entre uno y treinta.")
        async with self._fleet.database.sessions() as db:
            await serialize_write(db)
            state = await db.get(ArenaState, 1)
            if state is None or not state.accepting:
                raise ValueError("La ronda está cerrada; no se pueden iniciar campañas.")
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
            plan = CampaignPlan(
                campaign_id=campaign.id,
                generation=generation,
                max_mutations=max_mutations,
                generation_calls=0,
                stop_reason="",
            )
            db.add(plan)
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
            return campaign_view(campaign, plan)

    async def stop(self, campaign_id: str) -> dict[str, Any]:
        async with self._fleet.database.sessions() as db:
            await serialize_write(db)
            campaign = await db.get(Campaign, campaign_id)
            if campaign is None:
                raise ValueError("Campaña no encontrada.")
            if campaign.status == "running":
                campaign.status = "stopped"
                plan = await db.get(CampaignPlan, campaign_id)
                if plan is not None:
                    plan.stop_reason = "operator_stopped"
            await db.commit()
            return campaign_view(campaign, await db.get(CampaignPlan, campaign_id))

    async def all(self) -> list[dict[str, Any]]:
        async with self._fleet.database.sessions() as db:
            result = []
            for row in await db.scalars(select(Campaign).order_by(Campaign.created_at)):
                cases = list(
                    await db.scalars(
                        select(CampaignCaseRecord)
                        .where(CampaignCaseRecord.campaign_id == row.id)
                        .order_by(CampaignCaseRecord.index)
                    )
                )
                result.append(campaign_view(row, await db.get(CampaignPlan, row.id), cases))
            return result
