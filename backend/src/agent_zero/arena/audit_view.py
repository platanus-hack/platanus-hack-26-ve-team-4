"""Auditoría de chats: cada sesión con su historial completo, de la ronda actual o archivada.

Trabaja sobre filas planas (las mismas que guarda `round_snapshot`), así la ronda en curso y una
ronda archivada se leen con el mismo código.
"""

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from typing import Any

from fastapi.encoders import jsonable_encoder

from agent_zero.attempts.conversation import public_reply
from agent_zero.events.models import EventType
from agent_zero.events.schemas import TraceEvent
from agent_zero.oracles.trace_reader import tool_evidence
from agent_zero.sessions.reserved_alias import SWARM_PREFIX, TEST_PREFIX

Row = Mapping[str, Any]
Tables = Mapping[str, Sequence[Row]]
PROBER_ALIAS = "Prober"
PREVIEW_LENGTH = 120


def session_kind(session: Row) -> str:
    """Como `live.service.session_kind`, pero conserva las repeticiones del operador."""
    if str(session["id"]).startswith("internal-"):
        return "prober" if session["alias"] == PROBER_ALIAS else "replay"
    if str(session["alias"]).startswith(TEST_PREFIX):
        return "test"
    return "swarm" if str(session["alias"]).startswith(SWARM_PREFIX) else "audience"


def plain(rows: Iterable[Row]) -> list[dict[str, Any]]:
    """Fechas a ISO y enums a texto, igual que en el archivo de la ronda."""
    encoded: list[dict[str, Any]] = jsonable_encoder([dict(row) for row in rows])
    return encoded


def _seconds(start: str, end: str) -> float | None:
    try:
        delta = datetime.fromisoformat(end) - datetime.fromisoformat(start)
    except (TypeError, ValueError):
        return None
    return round(max(delta.total_seconds(), 0.0), 3)


def _ordered(attempts: Iterable[Row]) -> list[Row]:
    return sorted(attempts, key=lambda row: (str(row["created_at"]), str(row["id"])))


def conversations(attempts: list[Row], links: Iterable[Row]) -> list[list[Row]]:
    """Agrupa los intentos en conversaciones según `attempt_links`, en orden de creación."""
    previous = {str(link["attempt_id"]): str(link["previous_attempt_id"]) for link in links}
    thread_of: dict[str, int] = {}
    threads: list[list[Row]] = []
    for attempt in _ordered(attempts):
        parent = previous.get(str(attempt["id"]))
        index = thread_of.get(parent) if parent else None
        if index is None:
            index = len(threads)
            threads.append([])
        threads[index].append(attempt)
        thread_of[str(attempt["id"])] = index
    return threads


def _diversion(events: Iterable[Row], session_id: str) -> dict[str, Any] | None:
    route = next(
        (
            event
            for event in events
            if event["type"] == EventType.ROUTE_CHANGED.value and event["session_id"] == session_id
        ),
        None,
    )
    if route is None:
        return None
    data = route.get("data") or {}
    return {"reason": data.get("reason", ""), "at": route["timestamp"]}


def _violations(attempt: Row) -> list[str]:
    verdicts = (attempt.get("assessment") or {}).get("verdicts", [])
    return [str(verdict["objective_id"]) for verdict in verdicts if verdict.get("violated")]


def chat_summary(
    session: Row, attempts: list[Row], links: Sequence[Row], events: Sequence[Row]
) -> dict[str, Any]:
    ordered = _ordered(attempts)
    first = next((message for row in ordered for message in row["messages"]), "")
    outcomes = Counter(str(row["outcome"]) for row in ordered if row.get("outcome"))
    return {
        "id": session["id"],
        "alias": session["alias"],
        "kind": session_kind(session),
        "customer_id": session["customer_id"],
        "route": session["route"],
        "created_at": session["created_at"],
        "last_activity": max(
            (str(row["updated_at"]) for row in ordered), default=session["created_at"]
        ),
        "attempts": len(ordered),
        "conversations": len(conversations(ordered, links)),
        "outcomes": dict(outcomes),
        "violations": sum(1 for row in ordered if _violations(row)),
        "diversion": _diversion(events, str(session["id"])),
        "preview": first[:PREVIEW_LENGTH],
    }


def chat_index(tables: Tables) -> list[dict[str, Any]]:
    """Todas las sesiones de la ronda, de la más reciente a la más antigua."""
    by_session: dict[str, list[Row]] = {}
    for attempt in tables.get("attempts", []):
        by_session.setdefault(str(attempt["session_id"]), []).append(attempt)
    links = tables.get("attempt_links", [])
    events = tables.get("product_events", [])
    rows = [
        chat_summary(session, by_session.get(str(session["id"]), []), links, events)
        for session in tables.get("sessions", [])
    ]
    return sorted(rows, key=lambda row: str(row["last_activity"]), reverse=True)


def _tool_step(item: Any) -> dict[str, Any]:
    return {
        "event_id": item.event_id,
        "kind": item.kind,
        "tool": item.tool,
        "arguments": item.arguments,
        "provenance": item.provenance,
        "validator": item.validator,
        "effect": item.effect,
        "output": item.output,
    }


def audit_attempt(attempt: Row, events: Sequence[Row], position: int) -> dict[str, Any]:
    trace = [TraceEvent.model_validate(event) for event in events]
    assessment = attempt.get("assessment") or {}
    return {
        "id": attempt["id"],
        "position": position,
        "created_at": attempt["created_at"],
        "updated_at": attempt["updated_at"],
        "duration_seconds": _seconds(str(attempt["created_at"]), str(attempt["updated_at"])),
        "status": attempt["status"],
        "outcome": attempt.get("outcome"),
        "route": attempt["route"],
        "policy_version": attempt["policy_version"],
        "origin": attempt.get("origin", "audience"),
        "objective_id": attempt.get("objective_id"),
        "campaign_id": attempt.get("campaign_id"),
        "messages": attempt["messages"],
        # Lo que vio el participante: canarios redactados, como en su chat.
        "reply": public_reply(str(attempt.get("reply") or "")),
        "verdicts": assessment.get("verdicts", []),
        "detail": assessment.get("detail", ""),
        "tools": [_tool_step(item) for item in tool_evidence(trace)],
    }


def chat_detail(tables: Tables, session_id: str) -> dict[str, Any] | None:
    session = next((row for row in tables.get("sessions", []) if row["id"] == session_id), None)
    if session is None:
        return None
    attempts = [row for row in tables.get("attempts", []) if row["session_id"] == session_id]
    ids = {str(row["id"]) for row in attempts}
    events = sorted(
        (
            event
            for event in tables.get("product_events", [])
            if event.get("attempt_id") in ids or event.get("session_id") == session_id
        ),
        key=lambda event: int(event["id"]),
    )
    links = [row for row in tables.get("attempt_links", []) if row["attempt_id"] in ids]
    by_attempt: dict[str, list[Row]] = {}
    for event in events:
        if event.get("attempt_id"):
            by_attempt.setdefault(str(event["attempt_id"]), []).append(event)
    position = 0
    threads: list[dict[str, Any]] = []
    for thread in conversations(attempts, links):
        rows = []
        for attempt in thread:
            position += 1
            rows.append(audit_attempt(attempt, by_attempt.get(str(attempt["id"]), []), position))
        threads.append({"index": len(threads) + 1, "attempts": rows})
    return chat_summary(session, attempts, links, events) | {"threads": threads}
