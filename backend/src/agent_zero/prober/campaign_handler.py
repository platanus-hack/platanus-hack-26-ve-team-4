from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.attempts.attempt_query_service import AttemptQueryService
from agent_zero.attempts.attempt_submission_service import AttemptSubmissionService
from agent_zero.attempts.schemas import AttemptCreate
from agent_zero.fleet.fleet_builder import Fleet
from agent_zero.prober.campaign_models import Campaign
from agent_zero.prober.playbooks import campaign_case
from agent_zero.runtime.handlers import StepContext
from agent_zero.runtime.step_results import Advance, Complete, Fail, StepResult, Wait
from agent_zero.sessions.session_query_service import internal_session

CAMPAIGN_HANDLER = "prober_campaign"


class CampaignHandler:
    name = CAMPAIGN_HANDLER

    def __init__(
        self, fleet: Fleet, submissions: AttemptSubmissionService, attempts: AttemptQueryService
    ) -> None:
        self._fleet = fleet
        self._submissions = submissions
        self._attempts = attempts

    async def step(self, context: StepContext) -> StepResult:
        async with self._fleet.database.sessions() as db:
            campaign = await db.get(Campaign, str(context.input["campaign_id"]))
            if campaign is None:
                return Fail(reason="Campaña no encontrada.")
            if campaign.status != "running":
                return Complete(output={"status": campaign.status})
            if campaign.attempt_ids:
                latest = await self._attempts.get(campaign.attempt_ids[-1])
                if latest is not None and latest.outcome is None:
                    return Wait(
                        until=context.now + timedelta(seconds=0.05), checkpoint=context.checkpoint
                    )
                if latest is not None and "ModelLimitReachedError" in str(latest.assessment):
                    campaign.status = "exhausted"
            if len(campaign.attempt_ids) >= campaign.max_attempts or campaign.status == "exhausted":
                campaign.status = "exhausted"
                await db.commit()
                return Complete(
                    output={"status": "exhausted", "attempts": len(campaign.attempt_ids)}
                )
            return await self._enqueue(context, campaign, db)

    async def _enqueue(
        self, context: StepContext, campaign: Campaign, db: AsyncSession
    ) -> StepResult:
        customer, case, digest = campaign_case(len(campaign.attempt_ids), campaign.id)
        if digest in campaign.case_hashes:
            campaign.status = "exhausted"
            await db.commit()
            return Complete(output={"status": "exhausted", "reason": "duplicate_case"})
        session_id = context.checkpoint.get("session_id")
        if not session_id or context.checkpoint.get("index") != len(campaign.attempt_ids):
            session = await internal_session(db, customer, "Prober")
            return Advance(
                checkpoint={"session_id": session.id, "index": len(campaign.attempt_ids)}
            )
        try:
            attempt = await self._submissions.submit(
                str(session_id),
                AttemptCreate(
                    messages=case.messages,
                    objective_id=case.objective_id,
                    idempotency_key=case.case_id,
                ),
                origin="autonomous",
                campaign_id=campaign.id,
            )
        except HTTPException as error:
            if error.status_code in {409, 429}:
                return Wait(
                    until=context.now + timedelta(seconds=0.2), checkpoint=context.checkpoint
                )
            raise
        campaign.case_hashes = [*campaign.case_hashes, digest]
        campaign.attempt_ids = [*campaign.attempt_ids, attempt.id]
        await db.commit()
        return Advance(checkpoint={})
