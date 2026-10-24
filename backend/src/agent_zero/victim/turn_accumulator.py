import json
from typing import Any

MAX_TOOL_CALLS = 8
MAX_TOOL_INPUT = 16_000
MAX_RESPONSE_TEXT = 32_000


class TurnAccumulator:
    """Validate a native stream completely before allowing any proposed side effects."""

    def __init__(self) -> None:
        self.text: list[str] = []
        self.tools: list[dict[str, Any]] = []
        self._open: dict[int, dict[str, Any]] = {}
        self.stop_reason = ""
        self._text_length = 0

    def accept(self, event: dict[str, Any]) -> None:
        if self.stop_reason and any(key.startswith("contentBlock") for key in event):
            raise ValueError("El modelo produjo contenido después de finalizar el turno.")
        if "contentBlockStart" in event:
            self._start(event["contentBlockStart"])
        if "contentBlockDelta" in event:
            self._delta(event["contentBlockDelta"])
        if "contentBlockStop" in event:
            self._open.pop(int(event["contentBlockStop"].get("contentBlockIndex", 0)), None)
        if "messageStop" in event:
            if self.stop_reason or self._open:
                raise ValueError("El modelo terminó con bloques incompletos o más de un cierre.")
            self.stop_reason = str(event["messageStop"].get("stopReason", ""))

    def _start(self, block: dict[str, Any]) -> None:
        tool = block.get("start", {}).get("toolUse")
        if tool is None:
            return
        index = int(block.get("contentBlockIndex", 0))
        if index in self._open or len(self.tools) >= MAX_TOOL_CALLS:
            raise ValueError("El modelo propuso demasiadas herramientas o bloques superpuestos.")
        identity, name = tool.get("toolUseId"), tool.get("name")
        if not isinstance(identity, str) or not identity or len(identity) > 200:
            raise ValueError("La herramienta no tiene un identificador válido.")
        if not isinstance(name, str) or not name or len(name) > 80:
            raise ValueError("La herramienta no tiene un nombre válido.")
        item = {"id": identity, "name": name, "input": ""}
        self.tools.append(item)
        self._open[index] = item

    def _delta(self, block: dict[str, Any]) -> None:
        delta = block.get("delta", {})
        if "text" in delta:
            fragment = delta["text"]
            if not isinstance(fragment, str):
                raise ValueError("El modelo produjo un fragmento de texto inválido.")
            self._text_length += len(fragment)
            if self._text_length > MAX_RESPONSE_TEXT:
                raise ValueError("La respuesta del modelo excede el límite de texto.")
            self.text.append(fragment)
        if "toolUse" in delta:
            item = self._open.get(int(block.get("contentBlockIndex", 0)))
            fragment = delta["toolUse"].get("input", "")
            if item is None or not isinstance(fragment, str):
                raise ValueError("El modelo produjo argumentos fuera de un bloque de herramienta.")
            item["input"] += fragment
            if len(item["input"]) > MAX_TOOL_INPUT:
                raise ValueError("Los argumentos de la herramienta exceden el límite.")

    def finish(self) -> list[dict[str, Any]]:
        if self.stop_reason not in {"end_turn", "tool_use", "stop_sequence"} or self._open:
            raise ValueError("El modelo no terminó su turno de forma completa.")
        if bool(self.tools) != (self.stop_reason == "tool_use"):
            raise ValueError("El cierre del turno no corresponde a sus herramientas propuestas.")
        if len({item["id"] for item in self.tools}) != len(self.tools):
            raise ValueError("El modelo repitió identificadores de herramientas.")
        result = []
        for item in self.tools:
            arguments = json.loads(item["input"] or "{}")
            if not isinstance(arguments, dict):
                raise ValueError("Los argumentos de una herramienta deben ser un objeto JSON.")
            result.append({"id": item["id"], "name": item["name"], "arguments": arguments})
        return result
