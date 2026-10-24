import asyncio

from agent_zero.analyzer.enrichment import AnalyzerHandler, SemanticAnalyzerService
from agent_zero.analyzer.finding_service import FindingService
from agent_zero.analyzer.manifest import analyzer_manifest
from agent_zero.arena.models import ArenaState
from agent_zero.arena.round_service import RoundService
from agent_zero.attempts.attempt_execution_handler import AttemptExecutionHandler
from agent_zero.attempts.attempt_query_service import AttemptQueryService
from agent_zero.attempts.attempt_submission_service import AttemptSubmissionService
from agent_zero.attempts.attempt_worker import AttemptWorker
from agent_zero.evals.handler import EvaluationHandler
from agent_zero.evals.runner import EvaluationHarness, EvaluationRunner
from agent_zero.evals.service import EvaluationService
from agent_zero.events.broker import EventBroker
from agent_zero.events.event_store import EventStore
from agent_zero.fleet.fleet_builder import Fleet
from agent_zero.llm.gateway import LlmGateway
from agent_zero.oracles.assessment_service import AssessmentService
from agent_zero.patches.defense_scheduler import DefenseScheduler
from agent_zero.patches.explanation import PatchExplainer
from agent_zero.patches.validation_handler import PatchValidationHandler
from agent_zero.patches.validation_runner import ValidationRunner
from agent_zero.policies.policy_engine import BusinessPolicyEngine
from agent_zero.policies.policy_service import PolicyService
from agent_zero.prober.campaign_handler import CampaignHandler
from agent_zero.prober.manifest import prober_manifest
from agent_zero.registry.approval_service import ApprovalService
from agent_zero.registry.errors import VersionAlreadyPublishedError
from agent_zero.registry.publication_service import PublicationService
from agent_zero.routing.route_decision_service import RouteDecisionService
from agent_zero.victim.arena_manifest import arena_manifest, patch_manifest
from agent_zero.victim.environments import Environments
from agent_zero.victim.scenario_tools import ScenarioTools
from agent_zero.victim.tool_loop import ConversationExecutor
from agent_zero.victim.trace_observer import TraceObserver


class ProductCore:
    def __init__(self, fleet: Fleet, llm: LlmGateway, broker: EventBroker) -> None:
        self.fleet = fleet
        self.admission_lock = asyncio.Lock()
        self.maintenance_lock = asyncio.Lock()
        self._bootstrap_lock = asyncio.Lock()
        self._bootstrapped = False
        self.events = EventStore(fleet, broker)
        self.environments = Environments(fleet.settings)
        self.rounds = RoundService(fleet, self.events, self.environments)
        self.scenario = ScenarioTools(fleet, self.environments)
        self.engine = BusinessPolicyEngine(fleet.database, self.environments)
        self.observer = TraceObserver(self.events)
        self.executor = ConversationExecutor(fleet, llm, self.environments, self.scenario)
        self.policies = PolicyService(fleet.database, self.events, self.admission_lock)
        self.assessments = AssessmentService(self.environments)
        self.semantic = SemanticAnalyzerService(fleet)
        self.findings = FindingService(fleet.database, self.events, self.semantic.enqueue)
        self.attempts = AttemptQueryService(fleet.database)
        self.routing = RouteDecisionService(fleet, self.events)
        self.submissions = AttemptSubmissionService(
            fleet, self.policies, self.events, self.routing, self.admission_lock
        )
        self.validator = ValidationRunner(
            fleet, self.environments, self.executor, self.observer, self.engine
        )
        self.defense = DefenseScheduler(
            fleet, self.policies, self.findings, self.attempts, self.environments
        )
        self.worker = AttemptWorker(fleet, self.events, self.findings, self.defense)
        self.evaluation_runner = EvaluationRunner(
            fleet,
            EvaluationHarness(self.environments, self.executor, self.observer, self.scenario),
            llm,
        )
        self.evaluations = EvaluationService(fleet, self.policies, llm)
        self._llm = llm

    async def initialize(self) -> None:
        await self.environments.initialize()
        await self.policies.initialize()
        async with self.fleet.database.sessions() as db:
            if await db.get(ArenaState, 1) is None:
                db.add(ArenaState(id=1, accepting=True, revealed=False))
                await db.commit()
        await self.rounds.initialize()
        await self.events.restore()
        self.scenario.register()
        self.fleet.gateway.configure_business_layer(
            self.engine,
            self.observer,
            lambda context: self.environments.for_context(context).transaction(),
        )
        self.fleet.handlers.register(
            AttemptExecutionHandler(self.fleet, self.executor, self.events, self.assessments)
        )
        self.fleet.handlers.register(
            PatchValidationHandler(
                self.policies,
                self.attempts,
                self.events,
                self.validator,
                PatchExplainer(self.fleet, self._llm),
            )
        )

        self.fleet.handlers.register(
            CampaignHandler(self.fleet, self.submissions, self.attempts, self._llm, self.scenario)
        )
        self.fleet.handlers.register(AnalyzerHandler(self.fleet, self._llm, self.events))
        self.fleet.handlers.register(
            EvaluationHandler(self.fleet, self.evaluation_runner, self._llm)
        )

    async def ensure_agents(self) -> None:
        async with self._bootstrap_lock:
            if self._bootstrapped:
                return
            for manifest in (
                arena_manifest(),
                arena_manifest(decoy=True),
                patch_manifest(),
                prober_manifest(),
                analyzer_manifest(),
            ):
                async with self.fleet.database.sessions() as db:
                    try:
                        await PublicationService(db).publish(manifest)
                    except VersionAlreadyPublishedError:
                        continue
                    await ApprovalService(db).approve(
                        manifest.agent_id, manifest.version, "laboratorio"
                    )
            self._bootstrapped = True

    async def stop(self) -> None:
        await self.worker.stop()
        await self.environments.dispose()
