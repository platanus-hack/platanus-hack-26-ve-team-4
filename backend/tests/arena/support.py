import json
import re
import time
from collections.abc import AsyncIterator
from typing import Any

from fastapi.testclient import TestClient
from strands.types.content import Messages
from strands.types.streaming import StreamEvent
from strands.types.tools import ToolSpec

from agent_zero.llm.events import text_events
from agent_zero.llm.playback_model import PlaybackModel

OPERATOR = {"X-Operator-Secret": "change-me"}


def tool_events(name: str, arguments: dict[str, Any]) -> list[StreamEvent]:
    return [
        {"messageStart": {"role": "assistant"}},
        {"contentBlockStart": {"start": {"toolUse": {"toolUseId": "call-1", "name": name}}}},
        {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(arguments)}}}},
        {"contentBlockStop": {}},
        {"messageStop": {"stopReason": "tool_use"}},
    ]


class ScenarioPlayback(PlaybackModel):
    """A deterministic simulated provider; never installed in the application itself."""

    async def stream(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamEvent]:
        self.calls.append({"messages": messages})
        content = messages[-1]["content"]
        if any("toolResult" in item for item in content):
            results = [
                str(item["toolResult"]["content"]) for item in content if "toolResult" in item
            ]
            events = text_events("Resultado de la solicitud: " + " ".join(results))
        else:
            message = next(str(item["text"]) for item in reversed(content) if "text" in item)
            order = re.search(r"\b[A-C]-\d{4}\b", message)
            memory = re.search(r"preferencia (\w+) con valor (.+)", message, re.IGNORECASE)
            refund = re.search(r"[Rr]eembolsa (\d+(?:\.\d+)?) USD", message)
            if memory:
                events = tool_events(
                    "save_memory", {"key": memory[1], "value": memory[2].rstrip(".")}
                )
            elif refund and order:
                events = tool_events(
                    "request_refund", {"order_id": order[0], "amount": float(refund[1])}
                )
            elif order:
                events = tool_events("get_order", {"order_id": order[0]})
            else:
                events = tool_events("search_knowledge", {"query": message})
        for event in events:
            yield event


def join(client: TestClient, alias: str = "neo") -> dict[str, Any]:
    response = client.post("/api/sessions", json={"alias": alias, "accepted_rules": True})
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


def send(
    client: TestClient, session: dict[str, Any], message: str, key: str = "first"
) -> dict[str, Any]:
    response = client.post(
        "/api/attempts",
        headers={"Authorization": f"Bearer {session['token']}"},
        json={"message": message, "idempotency_key": key},
    )
    assert response.status_code == 202, response.text
    result: dict[str, Any] = response.json()
    return result


def wait_attempt(client: TestClient, attempt_id: str) -> dict[str, Any]:
    for _ in range(500):
        response = client.get(f"/api/operator/attempts/{attempt_id}", headers=OPERATOR)
        assert response.status_code == 200, response.text
        result: dict[str, Any] = response.json()
        if result["status"] in {"evaluated", "inconclusive"}:
            return result
        time.sleep(0.01)
    raise AssertionError(f"El intento {attempt_id} no terminó")


def foreign_order(session: dict[str, Any]) -> str:
    return "B-2001" if session["order_ids"][0].startswith("A") else "A-1001"


def active_policy(client: TestClient) -> dict[str, Any]:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        policies = client.get("/api/operator/policies", headers=OPERATOR).json()
        active: dict[str, Any] = next(row for row in policies if row["status"] == "active")
        if active["version"]:
            return active
        time.sleep(0.01)
    raise AssertionError(f"No se activó ninguna política: {policies}")
