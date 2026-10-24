"""Lee la traza de herramientas (v2, y v1 de runs ya persistidos) como `ToolEvidence`.

Contrato en docs/dominio/traza-herramientas.md. Falla cerrada: un `tool_completed` sin salida u
efecto legibles se marca `readable=False` y el intento queda inconcluso.
"""

import json
from typing import Any

from agent_zero.events.models import EventType
from agent_zero.events.schemas import TraceEvent
from agent_zero.oracles.schemas import ToolEvidence
from agent_zero.victim.trace_schemas import TRACE_SCHEMA_VERSION


def _object(value: Any) -> dict[str, Any] | None:
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except (ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _cents(value: Any) -> int:
    return round(float(value) * 100)


def legacy_effect(tool: str, output: dict[str, Any]) -> dict[str, Any] | None:
    """Reconstruye el efecto de un evento v1 a partir de su salida."""
    try:
        if tool == "get_order" and "customer_id" in output:
            return {
                "kind": "read",
                "order_id": output["order_id"],
                "owner_customer_id": output["customer_id"],
            }
        if tool == "request_refund" and output.get("approved") is True:
            after = _cents(output["refunded_total"])
            amount = _cents(output["amount"])
            return {
                "kind": "refund",
                "order_id": output["order_id"],
                "owner_customer_id": output["customer_id"],
                "amount_cents": amount,
                "refunded_before_cents": after - amount,
                "refunded_after_cents": after,
                "total_cents": _cents(output["total"]),
            }
        if tool == "save_memory" and output.get("saved") is True:
            return {
                "kind": "memory_write",
                "memory_id": output["memory_id"],
                "key": str(output["key"]),
                "value": str(output["value"]),
            }
    except (KeyError, TypeError, ValueError):
        return None
    return {"kind": "none"}


def tool_evidence(events: list[TraceEvent]) -> list[ToolEvidence]:
    result: list[ToolEvidence] = []
    for event in events:
        if not event.type.value.startswith("tool_"):
            continue
        data = event.data
        completed = event.type is EventType.TOOL_COMPLETED
        output = _object(data.get("output"))
        if data.get("schema_version") == TRACE_SCHEMA_VERSION:
            effect = data.get("effect")
        else:
            effect = legacy_effect(data["tool"], output) if completed and output else None
        result.append(
            ToolEvidence(
                event_id=event.id,
                kind=event.type.value,
                tool=data["tool"],
                arguments=data.get("arguments") or {},
                output=output or {},
                effect=effect if isinstance(effect, dict) else {},
                validator=data.get("validator") or "",
                operation_id=data.get("operation_id", ""),
                provenance=data.get("provenance") or {},
                readable=not completed or (output is not None and isinstance(effect, dict)),
            )
        )
    return result
