"""Señales de la auditoría por paso, por intento y por sesión.

Trabaja sobre filas planas (las mismas que guarda `round_snapshot`), igual que `audit_view`:
la etapa y el motivo de Armor, la familia de ataque de la campaña y el riesgo de la sesión se
calculan igual en la ronda en curso y en una archivada.
"""

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from agent_zero.events.models import EventType
from agent_zero.routing.session_risk import ToolOutcome, risk_score
from agent_zero.victim.fixtures import orders_for_customer

Row = Mapping[str, Any]
SESSION_TOOL_TYPES = frozenset({EventType.TOOL_DENIED.value, EventType.TOOL_COMPLETED.value})


def denial_info(events: Sequence[Row]) -> dict[int, dict[str, str]]:
    """Etapa, motivo y detalle de cada `tool_denied`, por id de evento."""
    info: dict[int, dict[str, str]] = {}
    for event in events:
        if event["type"] != EventType.TOOL_DENIED.value:
            continue
        data = event.get("data") or {}
        info[int(event["id"])] = {
            "stage": str(data.get("stage") or ""),
            "reason": str(data.get("reason") or ""),
            "detail": str(data.get("detail") or ""),
        }
    return info


def family_map(rows: Iterable[Row]) -> dict[str, str]:
    """Familia de ataque de cada intento de campaña (`campaign_cases`, por `attempt_id`)."""
    families: dict[str, str] = {}
    for row in rows:
        attempt_id = row.get("attempt_id")
        case = row.get("case_json")
        family = case.get("family") if isinstance(case, Mapping) else None
        if isinstance(attempt_id, str) and isinstance(family, str):
            families[attempt_id] = family
    return families


def _outcome(event: Row) -> ToolOutcome:
    data = event.get("data") or {}
    arguments = data.get("arguments")
    order_id = arguments.get("order_id") if isinstance(arguments, dict) else None
    validator = data.get("validator")
    return ToolOutcome(
        tool=str(data.get("tool", "")),
        denied=event["type"] == EventType.TOOL_DENIED.value,
        validator=validator if isinstance(validator, str) else None,
        order_id=order_id if isinstance(order_id, str) else None,
    )


def _own_orders(customer_id: str) -> list[str]:
    try:
        return [order.order_id for order in orders_for_customer(customer_id)]
    except ValueError:
        return []


def session_risk(events: Sequence[Row], customer_id: str) -> tuple[int, list[dict[str, Any]]]:
    """Puntaje de riesgo de la sesión y las validaciones que más la denegaron."""
    outcomes = [_outcome(event) for event in events if event["type"] in SESSION_TOOL_TYPES]
    denials = Counter(
        str(outcome.validator) for outcome in outcomes if outcome.denied and outcome.validator
    )
    signals = [
        {"validator": validator, "count": count}
        for validator, count in sorted(denials.items(), key=lambda item: (-item[1], item[0]))
    ]
    return risk_score(outcomes, _own_orders(customer_id)), signals


def tool_step(item: Any, denial: Mapping[str, str]) -> dict[str, Any]:
    """Paso de herramienta de la auditoría; etapa, motivo y detalle solo si fue denegado."""
    return {
        "event_id": item.event_id,
        "kind": item.kind,
        "tool": item.tool,
        "arguments": item.arguments,
        "provenance": item.provenance,
        "validator": item.validator,
        "effect": item.effect,
        "output": item.output,
        # Etapa y motivo de Armor; vacíos si el paso no fue denegado.
        "stage": denial.get("stage", ""),
        "reason": denial.get("reason", ""),
        "detail": denial.get("detail", ""),
    }
