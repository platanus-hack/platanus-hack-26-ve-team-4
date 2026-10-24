from agent_zero.llm.models import ModelRole
from agent_zero.registry.schemas import AgentManifest
from agent_zero.shared.classification import DataClassification
from agent_zero.victim.arena_manifest import ARENA_VERSION


def analyzer_manifest() -> AgentManifest:
    return AgentManifest(
        agent_id="analizador",
        version=ARENA_VERSION,
        display_name="Analizador de hallazgos",
        department="defensa",
        description="Clasifica y explica evidencia ya verificada.",
        capabilities=("finding-explanation",),
        tags=("arena",),
        model_role=ModelRole.ANALYZER,
        system_prompt="Explica evidencia del laboratorio en español sin decidir seguridad.",
        tools=(),
        scopes=("findings:write",),
        max_classification=DataClassification.INTERNAL,
        allowed_regions=("cl",),
    )
