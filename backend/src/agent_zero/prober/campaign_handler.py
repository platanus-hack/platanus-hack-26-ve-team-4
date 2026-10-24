from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select

from agent_zero.agent_gateway.business_policy import CallContext
from agent_zero.arena.round_models import RoundArchive
from agent_zero.arena.transactions import serialize_write
from agent_zero.attempts.attempt_query_service import AttemptQueryService
from agent_zero.attempts.attempt_submission_service import AttemptSubmissionService
from agent_zero.attempts.models import AttemptOutcome
from agent_zero.attempts.schemas import AttemptCreate
from agent_zero.events.event_store import EventStore
from agent_zero.fleet.fleet_builder import Fleet
from agent_zero.llm.gateway import LlmGateway
from agent_zero.prober.adaptive_planner import AdaptivePlanner, Finish, Hold
from agent_zero.prober.campaign_models import Campaign, CampaignCaseRecord, CampaignPlan
from agent_zero.prober.mutation import mutate_case
from agent_zero.prober.playbooks import campaign_case, case_digest
from agent_zero.prober.schemas import AttackCase
from agent_zero.runtime.handlers import StepContext
from agent_zero.runtime.step_results import Advance, Complete, Fail, StepResult, Wait
from agent_zero.sessions.session_query_service import internal_session
from agent_zero.victim.scenario_tools import ScenarioTools

CAMPAIGN_HANDLER = "prober_campaign"


class CampaignHandler:
    name = CAMPAIGN_HANDLER

    def __init__(
        self,
        fleet: Fleet,
        submissions: AttemptSubmissionService,
        attempts: AttemptQueryService,
        llm: LlmGateway | None = None,
        scenario: ScenarioTools | None = None,
    ) -> None:
        self._fleet = fleet
        self._submissions = submissions
        self._attempts = attempts
        self._llm = llm
        self._scenario = scenario
        self._planner = AdaptivePlanner(fleet.settings, fleet.clock)

    def attach_events(self, events: EventStore) -> None:
        self._planner = AdaptivePlanner(self._fleet.settings, self._fleet.clock, events)

    async def step(self, context: StepContext) -> StepResult:
        campaign_id = str(context.input["campaign_id"])
        async with self._fleet.database.sessions() as db:
            await serialize_write(db)
            if await db.scalar(select(RoundArchive.id).where(RoundArchive.status == "resetting")):
                return self._wait(context)
            campaign = await db.get(Campaign, campaign_id)
            if campaign is None:
                return Fail(reason="Campaña no encontrada.")
            if campaign.status != "running":
                return Complete(output={"status": campaign.status})
            plan = await db.get(CampaignPlan, campaign_id)
            if plan is None:  # Resume campaigns created by the previous implementation.
                plan = CampaignPlan(
                    campaign_id=campaign_id,
                    generation="templates",
                    max_mutations=30,
                    generation_calls=0,
                    stop_reason="",
                )
                db.add(plan)
                await db.commit()
        return await self._continue(context, campaign, plan)

    async def _continue(
        self, context: StepContext, campaign: Campaign, plan: CampaignPlan
    ) -> StepResult:
        campaign_id = campaign.id
        if campaign.attempt_ids:
            latest = await self._attempts.get(campaign.attempt_ids[-1])
            if latest is not None and (
                latest.outcome is None
                or (
                    latest.outcome is AttemptOutcome.CONFIRMED_VIOLATION
                    and not latest.defense_processed
                )
            ):
                return self._wait(context)
            if latest is not None and "ModelLimitReachedError" in str(latest.assessment):
                return await self._finish(campaign_id, "llm_budget_exhausted")
        if len(campaign.attempt_ids) >= campaign.max_attempts:
            return await self._finish(campaign_id, "attempt_budget_exhausted")
        record = await self._next_record(campaign, plan)
        if isinstance(record, CampaignCaseRecord):
            return await self._act_on_record(context, campaign, record)
        return await self._conclude(context, campaign_id, record)

    async def _conclude(
        self, context: StepContext, campaign_id: str, planned: Hold | Finish | None
    ) -> StepResult:
        if isinstance(planned, Hold):
            return self._wait(context)
        return await self._finish(
            campaign_id, planned.reason if planned else "unique_cases_exhausted"
        )

    async def _act_on_record(
        self,
        context: StepContext,
        campaign: Campaign,
        record: CampaignCaseRecord,
    ) -> StepResult:
        if record.status in {"pending_generation", "generating"}:
            return await self._generate(campaign, record)
        if record.status == "generation_error":
            return await self._finish(campaign.id, "generator_failed")
        if record.digest in campaign.case_hashes:
            async with self._fleet.database.sessions() as db:
                await serialize_write(db)
                row = await db.get(CampaignCaseRecord, (campaign.id, record.index))
                if row is not None:
                    row.status = "duplicate"
                    await db.commit()
            return Advance(checkpoint={})
        return await self._enqueue(context, campaign, record)

    def _wait(self, context: StepContext) -> Wait:
        return Wait(until=context.now + timedelta(seconds=0.1), checkpoint={})

    async def _next_record(
        self, campaign: Campaign, plan: CampaignPlan
    ) -> CampaignCaseRecord | Hold | Finish | None:
        async with self._fleet.database.sessions() as db:
            await serialize_write(db)
            rows = list(
                await db.scalars(
                    select(CampaignCaseRecord)
                    .where(CampaignCaseRecord.campaign_id == campaign.id)
                    .order_by(CampaignCaseRecord.index)
                )
            )
            pending = next(
                (row for row in rows if row.status not in {"submitted", "duplicate"}), None
            )
            if pending is not None:
                return pending
            index = max([row.index + 1 for row in rows] + [len(campaign.attempt_ids)])
            if plan.generation == "adaptive":
                return await self._planner.next(db, campaign, index)
            if index >= 30:
                return None
            customer, case, digest = campaign_case(index, campaign.id)
            row = CampaignCaseRecord(
                campaign_id=campaign.id,
                index=index,
                status="pending_generation" if plan.generation == "llm" else "ready",
                customer_id=customer,
                case_json=case.model_dump(mode="json"),
                digest=digest,
                session_id=None,
                attempt_id=None,
                error="",
            )
            db.add(row)
            await db.commit()
            return row

    async def _generate(self, campaign: Campaign, record: CampaignCaseRecord) -> StepResult:
        async with self._fleet.database.sessions() as db:
            await serialize_write(db)
            live = await db.get(Campaign, campaign.id)
            persisted = await db.get(CampaignPlan, campaign.id)
            row = await db.get(CampaignCaseRecord, (campaign.id, record.index))
            if live is None or live.status != "running":
                return Complete(output={"status": "stopped"})
            if persisted is None or row is None:
                return Fail(reason="Falta el plan durable de la campaña.")
            if persisted.generation_calls >= persisted.max_mutations:
                live.status = "exhausted"
                persisted.stop_reason = "mutation_budget_exhausted"
                await db.commit()
                return Complete(output={"status": "exhausted", "reason": persisted.stop_reason})
            if row.status == "ready":
                return Advance(checkpoint={})
            persisted.generation_calls += 1
            row.status = "generating"
            await db.commit()  # Reserve before calling; recovery cannot reset this budget.
        try:
            if self._llm is None:
                raise ValueError("El generador LLM no está configurado.")
            case = await mutate_case(
                self._llm, campaign.id, AttackCase.model_validate(record.case_json)
            )
            error = ""
        except Exception as failure:
            case = None
            error = type(failure).__name__
        async with self._fleet.database.sessions() as db:
            await serialize_write(db)
            row = await db.get(CampaignCaseRecord, (campaign.id, record.index))
            if row is None:
                return Fail(reason="Se perdió el caso de campaña.")
            row.error = error
            row.status = "ready" if case is not None else "generation_error"
            if case is not None:
                row.case_json = case.model_dump(mode="json")
                row.digest = case_digest(record.customer_id, case)
            await db.commit()
        return Advance(checkpoint={})

    async def _enqueue(
        self, context: StepContext, campaign: Campaign, record: CampaignCaseRecord
    ) -> StepResult:
        case = AttackCase.model_validate(record.case_json)
        if record.session_id is None:
            async with self._fleet.database.sessions() as db:
                session = await internal_session(db, record.customer_id, "Prober")
                row = await db.get(CampaignCaseRecord, (campaign.id, record.index))
                if row is not None:
                    row.session_id = session.id
                    await db.commit()
            return Advance(checkpoint={})
        if case.fixture is not None:
            if self._scenario is None:
                return Fail(reason="La superficie controlada no está configurada.")
            await self._scenario.install_fixture(
                CallContext(
                    attempt_id=case.case_id,
                    session_id=record.session_id,
                    session_customer_id=record.customer_id,
                    environment="protected",
                    policy_version=0,
                    run_id=context.run_id,
                    campaign_id=campaign.id,
                ),
                case.fixture,
            )
        # Re-read status immediately before admission so stop does not enqueue another case.
        async with self._fleet.database.sessions() as db:
            await serialize_write(db)
            live = await db.get(Campaign, campaign.id)
            if live is None or live.status != "running":
                return Complete(output={"status": "stopped"})
        try:
            attempt = await self._submissions.submit(
                record.session_id,
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
                return self._wait(context)
            raise
        async with self._fleet.database.sessions() as db:
            await serialize_write(db)
            live = await db.get(Campaign, campaign.id)
            row = await db.get(CampaignCaseRecord, (campaign.id, record.index))
            if live is None or row is None:
                return Fail(reason="Se perdió la campaña tras admitir el intento.")
            if attempt.id not in live.attempt_ids:
                live.case_hashes = [*live.case_hashes, record.digest]
                live.attempt_ids = [*live.attempt_ids, attempt.id]
            row.attempt_id = attempt.id
            row.status = "submitted"
            await db.commit()
        return Advance(checkpoint={})

    async def _finish(self, campaign_id: str, reason: str) -> Complete:
        async with self._fleet.database.sessions() as db:
            await serialize_write(db)
            row = await db.get(Campaign, campaign_id)
            plan = await db.get(CampaignPlan, campaign_id)
            if row is not None and row.status == "running":
                row.status = "exhausted"
                if plan is not None:
                    plan.stop_reason = reason
                await db.commit()
            return Complete(
                output={
                    "status": row.status if row else "missing",
                    "reason": reason,
                    "attempts": len(row.attempt_ids) if row else 0,
                }
            )
