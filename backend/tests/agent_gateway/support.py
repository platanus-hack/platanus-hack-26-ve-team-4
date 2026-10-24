from dataclasses import dataclass, field
from typing import Any

from agent_zero.agent_gateway.agent_gateway import AgentGateway
from agent_zero.agent_gateway.gateway_auditor import GatewayAuditor
from agent_zero.agent_gateway.gateway_parts import GatewayParts
from agent_zero.agent_gateway.identity_stage import IdentityStage
from agent_zero.agent_gateway.manifest_source import RegistryManifestSource
from agent_zero.agent_gateway.policy_engine import PolicyEngine
from agent_zero.agent_gateway.rate_limiter import RateLimiter
from agent_zero.agent_gateway.schemas import ToolSpec
from agent_zero.agent_gateway.stage_tracer import StageTracer
from agent_zero.agent_gateway.tool_registry import ToolRegistry
from agent_zero.armor.model_armor import ModelArmor
from agent_zero.config import Settings
from agent_zero.identity.credential_issuer import CredentialIssuer
from agent_zero.identity.schemas import AgentGrant, AgentPrincipal, IssuedCredential
from agent_zero.llm.models import ModelRole
from agent_zero.registry.approval_service import ApprovalService
from agent_zero.registry.grant_service import grant_for
from agent_zero.registry.publication_service import PublicationService
from agent_zero.registry.schemas import AgentManifest, ToolGrant
from agent_zero.shared.classification import DataClassification
from agent_zero.shared.database import Database
from agent_zero.telemetry.audit_log import AuditLog
from agent_zero.telemetry.otel_setup import Telemetry, build_telemetry
from tests.identity.conftest import FakeClock

ORDER_OUTPUT = "Pedido A-1001 en camino. Contacto: cliente@example.com"


def build_manifest(**overrides: Any) -> AgentManifest:
    fields: dict[str, Any] = {
        "agent_id": "agente-soporte",
        "version": "1.0.0",
        "display_name": "Agente de Soporte",
        "department": "soporte",
        "description": "Atiende consultas de pedidos.",
        "capabilities": ("pedidos",),
        "tags": ("soporte",),
        "model_role": ModelRole.VICTIM,
        "system_prompt": "Eres un asistente de soporte. Responde con precisión.",
        "tools": (
            ToolGrant(
                name="get_order",
                description="Obtiene un pedido por su número.",
                classification=DataClassification.INTERNAL,
            ),
        ),
        "scopes": ("tool:get_order", "tool:get_ledger", "tool:get_secret"),
        "max_classification": DataClassification.INTERNAL,
        "allowed_regions": ("cl",),
    }
    fields.update(overrides)
    return AgentManifest(**fields)


@dataclass
class Harness:
    gateway: AgentGateway
    issuer: CredentialIssuer
    audit: AuditLog
    telemetry: Telemetry
    database: Database
    clock: FakeClock
    calls: list[dict[str, Any]] = field(default_factory=list)
    output: str = ORDER_OUTPUT
    failure: Exception | None = None

    async def approve(self, manifest: AgentManifest | None = None) -> IssuedCredential:
        manifest = manifest or build_manifest()
        async with self.database.sessions() as db:
            await PublicationService(db, clock=self.clock).publish(manifest)
            await ApprovalService(db, self.clock).approve(
                manifest.agent_id, manifest.version, "operador"
            )
            grant = await grant_for(db, manifest.agent_id, manifest.version)
        return self.issuer.issue(grant)


def build_harness(settings: Settings, database: Database, clock: FakeClock) -> Harness:
    telemetry = build_telemetry(settings.model_copy(update={"otel_exporter": "memory"}))
    audit = AuditLog.from_settings(settings, clock)
    armor = ModelArmor()
    tools = ToolRegistry()
    calls: list[dict[str, Any]] = []
    harness = Harness(
        gateway=AgentGateway(
            GatewayParts(
                tools=tools,
                identity=IdentityStage(database.sessions, settings, clock),
                manifests=RegistryManifestSource(database.sessions),
                policy=PolicyEngine(
                    settings, RateLimiter(settings.gateway_rate_limit_per_minute, clock)
                ),
                armor=armor,
                auditor=GatewayAuditor(audit, armor.redact_pii),
                tracer=StageTracer(telemetry, armor.redact_pii),
            )
        ),
        issuer=CredentialIssuer(settings, clock),
        audit=audit,
        telemetry=telemetry,
        database=database,
        clock=clock,
        calls=calls,
    )

    async def get_order(arguments: dict[str, Any]) -> str:
        if harness.failure is not None:
            raise harness.failure
        calls.append(arguments)
        return harness.output

    def register(name: str, classification: DataClassification, region: str = "cl") -> None:
        spec = ToolSpec(
            name=name,
            classification=classification,
            region=region,
            required_scope=f"tool:{name}",
        )
        tools.register(spec, get_order)

    register("get_order", DataClassification.INTERNAL)
    register("get_ledger", DataClassification.INTERNAL, region="ve")
    register("get_secret", DataClassification.RESTRICTED)
    return harness


def grants(*names: str) -> tuple[ToolGrant, ...]:
    return tuple(
        ToolGrant(
            name=name,
            description=f"Consulta {name}.",
            classification=DataClassification.INTERNAL,
        )
        for name in names
    )


def grant_from(principal: AgentPrincipal) -> AgentGrant:
    return AgentGrant(
        agent_id=principal.agent_id,
        version=principal.version,
        department=principal.department,
        scopes=principal.scopes,
        clearance=principal.clearance,
        allowed_regions=principal.allowed_regions,
    )
