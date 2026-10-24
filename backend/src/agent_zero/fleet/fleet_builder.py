from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from strands.models.model import Model

from agent_zero.agent_gateway.agent_gateway import AgentGateway
from agent_zero.agent_gateway.gateway_auditor import GatewayAuditor
from agent_zero.agent_gateway.gateway_parts import GatewayParts
from agent_zero.agent_gateway.identity_stage import IdentityStage
from agent_zero.agent_gateway.manifest_source import RegistryManifestSource
from agent_zero.agent_gateway.policy_engine import PolicyEngine
from agent_zero.agent_gateway.rate_limiter import RateLimiter
from agent_zero.agent_gateway.stage_tracer import StageTracer
from agent_zero.agent_gateway.tool_registry import ToolRegistry
from agent_zero.armor.model_armor import ModelArmor
from agent_zero.config import Settings
from agent_zero.fleet.gateway_tool_access import GatewayToolProvider
from agent_zero.fleet.registry_admission import RegistryAdmission
from agent_zero.fleet.token_vault import TokenVault
from agent_zero.fleet.vault_principal_guard import VaultPrincipalGuard
from agent_zero.identity.credential_issuer import CredentialIssuer
from agent_zero.llm.traced_model import TracedModel
from agent_zero.memory_bank.memory_cipher import MemoryCipher
from agent_zero.memory_bank.principal_guard import PrincipalGuard
from agent_zero.runtime.handler_registry import HandlerRegistry
from agent_zero.runtime.run_worker import RunWorker
from agent_zero.runtime.wiring import RuntimeWiring
from agent_zero.shared.clock import utc_now
from agent_zero.shared.database import Database
from agent_zero.telemetry.audit_log import AuditLog
from agent_zero.telemetry.otel_setup import Telemetry, build_telemetry


@dataclass(frozen=True)
class Fleet:
    settings: Settings
    database: Database
    clock: Callable[[], datetime]
    telemetry: Telemetry
    audit: AuditLog
    armor: ModelArmor
    issuer: CredentialIssuer
    cipher: MemoryCipher
    memory_guard: PrincipalGuard
    tools: ToolRegistry
    handlers: HandlerRegistry
    gateway: AgentGateway
    admission: RegistryAdmission
    worker: RunWorker
    owns_telemetry: bool

    def trace_model(self, model: Model, role: str) -> Model:
        return TracedModel(model, role, self.telemetry.tracer)

    def start(self) -> None:
        self.worker.start()

    async def stop(self) -> None:
        await self.worker.stop()
        if self.owns_telemetry:
            self.telemetry.shutdown()


def build_fleet(
    settings: Settings,
    database: Database,
    clock: Callable[[], datetime] = utc_now,
    telemetry: Telemetry | None = None,
) -> Fleet:
    owned = telemetry is None
    active = telemetry or build_telemetry(settings)
    armor = ModelArmor()
    audit = AuditLog.from_settings(settings, clock)
    issuer = CredentialIssuer(settings, clock)
    vault = TokenVault(clock)
    tools = ToolRegistry()
    handlers = HandlerRegistry()
    gateway = AgentGateway(
        GatewayParts(
            tools=tools,
            identity=IdentityStage(database.sessions, settings, clock),
            manifests=RegistryManifestSource(database.sessions),
            policy=PolicyEngine(
                settings, RateLimiter(settings.gateway_rate_limit_per_minute, clock)
            ),
            armor=armor,
            auditor=GatewayAuditor(audit, armor.redact_pii),
            tracer=StageTracer(active, armor.redact_pii),
        )
    )
    admission = RegistryAdmission(database.sessions, issuer, vault, clock)
    wiring = RuntimeWiring(
        sessions=database.sessions,
        registry=handlers,
        admission=admission,
        clock=clock,
        telemetry=active,
        tools=GatewayToolProvider(gateway, vault),
    )
    return Fleet(
        settings=settings,
        database=database,
        clock=clock,
        telemetry=active,
        audit=audit,
        armor=armor,
        issuer=issuer,
        cipher=MemoryCipher.from_settings(settings),
        memory_guard=VaultPrincipalGuard(database.sessions, settings, vault, clock),
        tools=tools,
        handlers=handlers,
        gateway=gateway,
        admission=admission,
        worker=RunWorker(wiring, settings),
        owns_telemetry=owned,
    )
