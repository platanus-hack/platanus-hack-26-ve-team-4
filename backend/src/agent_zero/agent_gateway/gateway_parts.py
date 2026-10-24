from dataclasses import dataclass

from agent_zero.agent_gateway.gateway_auditor import GatewayAuditor
from agent_zero.agent_gateway.identity_stage import IdentityStage
from agent_zero.agent_gateway.manifest_source import ManifestSource
from agent_zero.agent_gateway.policy_engine import PolicyEngine
from agent_zero.agent_gateway.stage_tracer import StageTracer
from agent_zero.agent_gateway.tool_registry import ToolRegistry
from agent_zero.armor.model_armor import ModelArmor


@dataclass(frozen=True)
class GatewayParts:
    tools: ToolRegistry
    identity: IdentityStage
    manifests: ManifestSource
    policy: PolicyEngine
    armor: ModelArmor
    auditor: GatewayAuditor
    tracer: StageTracer
