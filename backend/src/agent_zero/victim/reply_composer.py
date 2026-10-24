import json
from collections.abc import Sequence
from typing import Any

from strands.models.model import Model

from agent_zero.armor.model_armor import ModelArmor
from agent_zero.armor.models import ArmorAction, Surface
from agent_zero.llm.context import declaring_prompt_version
from agent_zero.victim.manifest import SUPPORT_SYSTEM_PROMPT

PROMPT_VERSION = "support-reply-v1"
BLOCKED_REPLY = "No puedo ayudarte con esa solicitud; un agente humano revisará tu caso."


def _brief(order: dict[str, Any], articles: Sequence[str], memories: Sequence[str]) -> str:
    return json.dumps(
        {"pedido": order, "base_de_conocimiento": list(articles), "historial": list(memories)},
        ensure_ascii=False,
    )


def _text(event: Any) -> str:
    delta = event.get("contentBlockDelta", {}).get("delta", {}) if isinstance(event, dict) else {}
    text = delta.get("text", "")
    return text if isinstance(text, str) else ""


class ReplyComposer:
    def __init__(self, model: Model, armor: ModelArmor) -> None:
        self._model = model
        self._armor = armor

    async def compose(
        self,
        message: str,
        order: dict[str, Any],
        articles: Sequence[str],
        memories: Sequence[str],
    ) -> str:
        prompt: Any = [
            {
                "role": "user",
                "content": [
                    {"text": f"Contexto: {_brief(order, articles, memories)}"},
                    {"text": f"Mensaje del cliente: {message}"},
                ],
            }
        ]
        with declaring_prompt_version(PROMPT_VERSION):
            pieces = [
                _text(event)
                async for event in self._model.stream(prompt, system_prompt=SUPPORT_SYSTEM_PROMPT)
            ]
        reply = "".join(pieces).strip()
        verdict = self._armor.screen(reply, Surface.MODEL_OUTPUT)
        if verdict.action is ArmorAction.BLOCK:
            return BLOCKED_REPLY
        return verdict.sanitized_text or reply
