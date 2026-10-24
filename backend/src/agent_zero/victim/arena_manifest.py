from agent_zero.llm.models import ModelRole
from agent_zero.registry.schemas import AgentManifest, ToolGrant
from agent_zero.shared.classification import DataClassification
from agent_zero.victim.honeytool_schemas import HONEYTOOL_DESCRIPTIONS
from agent_zero.victim.tool_loop import SYSTEM_PROMPT
from agent_zero.victim.tool_schemas import DESCRIPTIONS

ARENA_VERSION = "2.2.0"  # 2.1.0: herramientas cebo del señuelo. 2.2.0: región `ve`.
ARENA_HANDLER = "arena_attempt"
PATCH_HANDLER = "validate_patch"


def arena_manifest(decoy: bool = False) -> AgentManifest:
    descriptions = DESCRIPTIONS | HONEYTOOL_DESCRIPTIONS if decoy else DESCRIPTIONS
    return AgentManifest(
        agent_id="soporte-senuelo" if decoy else "soporte-tienda",
        version=ARENA_VERSION,
        display_name="Soporte de la arena",
        department="soporte",
        description="Atiende pedidos, reembolsos y preferencias del laboratorio sintético.",
        capabilities=("pedidos", "reembolsos", "preferencias"),
        tags=("arena",),
        model_role=ModelRole.DECOY if decoy else ModelRole.VICTIM,
        system_prompt=SYSTEM_PROMPT,
        tools=tuple(
            ToolGrant(
                name=name, description=description, classification=DataClassification.INTERNAL
            )
            for name, description in descriptions.items()
        ),
        scopes=(*(f"tool:{name}" for name in descriptions), "memory:read", "memory:write"),
        max_classification=DataClassification.CONFIDENTIAL,
        allowed_regions=("ve",),
    )


def patch_manifest() -> AgentManifest:
    return AgentManifest(
        agent_id="generador-parches",
        version=ARENA_VERSION,
        display_name="Validador de políticas",
        department="defensa",
        description="Verifica controles declarativos del laboratorio en datos aislados.",
        capabilities=("validacion-politicas",),
        tags=("arena",),
        model_role=ModelRole.PATCHER,
        system_prompt="Explica controles de política con evidencia del laboratorio.",
        tools=(),
        scopes=("policies:propose",),
        max_classification=DataClassification.INTERNAL,
        allowed_regions=("ve",),
    )
