from collections.abc import Iterator

from agent_zero.armor.model_armor import ModelArmor
from agent_zero.armor.models import Surface
from agent_zero.registry.schemas import AgentManifest


def _texts(manifest: AgentManifest) -> Iterator[tuple[str, str, Surface]]:
    yield "prompt del sistema", manifest.system_prompt, Surface.SYSTEM_PROMPT
    yield "descripción", manifest.description, Surface.TOOL_DESCRIPTION
    yield "nombre", manifest.display_name, Surface.TOOL_DESCRIPTION
    for capability in manifest.capabilities:
        yield "capacidad", capability, Surface.TOOL_DESCRIPTION
    for tag in manifest.tags:
        yield "etiqueta", tag, Surface.TOOL_DESCRIPTION
    for tool in manifest.tools:
        yield f"herramienta {tool.name}", tool.description, Surface.TOOL_DESCRIPTION
        yield f"nombre de herramienta {tool.name}", tool.name, Surface.TOOL_DESCRIPTION


def screen_manifest(manifest: AgentManifest, armor: ModelArmor) -> tuple[str, ...]:
    reasons: list[str] = []
    for label, text, surface in _texts(manifest):
        verdict = armor.screen(text, surface)
        if verdict.blocked:
            reasons.extend(f"{label}: {finding.detail}" for finding in verdict.findings)
    return tuple(reasons)
