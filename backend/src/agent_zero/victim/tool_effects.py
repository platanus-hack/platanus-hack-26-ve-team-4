import json
from typing import Any

from agent_zero.agent_gateway.tool_registry import ToolOutput
from agent_zero.victim.trace_schemas import TRACE_SCHEMA_VERSION, ToolEffect

# La operación idempotente guarda salida y efecto juntos para que un reintento devuelva ambos.
# No hay migraciones: van en la misma columna de texto, marcadas con la versión del contrato.
STORED_VERSION = "trace_schema_version"


def stored_operation(output: dict[str, Any], effect: ToolEffect) -> str:
    return json.dumps(
        {
            STORED_VERSION: TRACE_SCHEMA_VERSION,
            "output": output,
            "effect": effect.model_dump(mode="json"),
        },
        ensure_ascii=False,
    )


def replayed_operation(stored: str) -> ToolOutput:
    data = json.loads(stored)
    if isinstance(data, dict) and data.get(STORED_VERSION) == TRACE_SCHEMA_VERSION:
        return ToolOutput(json.dumps(data["output"], ensure_ascii=False), data["effect"])
    # Operación guardada con la v1: no declaró su efecto y los oráculos la tratarán como ilegible.
    return ToolOutput(stored)


def tool_output(output: dict[str, Any], effect: ToolEffect) -> ToolOutput:
    return ToolOutput(json.dumps(output, ensure_ascii=False), effect.model_dump(mode="json"))
