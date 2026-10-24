from dataclasses import dataclass
from typing import Any

from agent_zero.armor.model_armor import ModelArmor
from agent_zero.armor.models import ArmorAction, Surface, ThreatKind


@dataclass
class ScreenedArguments:
    arguments: dict[str, Any]
    blocked: bool = False
    redacted: bool = False
    kinds: tuple[ThreatKind, ...] = ()


class _Walker:
    def __init__(self, armor: ModelArmor) -> None:
        self._armor = armor
        self.blocked = False
        self.redacted = False
        self.kinds: set[ThreatKind] = set()

    def walk(self, value: Any) -> Any:
        if isinstance(value, str):
            return self._text(value)
        if isinstance(value, dict):
            return {key: self.walk(item) for key, item in value.items()}
        if isinstance(value, list | tuple):
            return [self.walk(item) for item in value]
        return value

    def _text(self, text: str) -> str:
        verdict = self._armor.screen(text, Surface.USER_INPUT)
        self.kinds.update(finding.kind for finding in verdict.findings)
        if verdict.action is ArmorAction.BLOCK:
            self.blocked = True
            return text
        if verdict.action is ArmorAction.REDACT and verdict.sanitized_text is not None:
            self.redacted = True
            return verdict.sanitized_text
        return text


def screen_arguments(armor: ModelArmor, arguments: dict[str, Any]) -> ScreenedArguments:
    walker = _Walker(armor)
    cleaned = {key: walker.walk(item) for key, item in arguments.items()}
    kinds = tuple(sorted(walker.kinds, key=lambda kind: kind.value))
    return ScreenedArguments(cleaned, walker.blocked, walker.redacted, kinds)
