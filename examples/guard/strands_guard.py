from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from typing import Any

from strands.hooks import (
    AfterToolCallEvent,
    BeforeToolCallEvent,
    HookProvider,
    HookRegistry,
)

try:
    from .agent_zero_guard import AgentZeroGuard
except ImportError:
    from agent_zero_guard import AgentZeroGuard

MAX_SEGMENTS = 200
MAX_TEXT = 20000


def block_text(block: dict[str, Any]) -> str:
    if "text" in block:
        return str(block["text"])
    if "json" in block:
        return json.dumps(block["json"], ensure_ascii=False)
    return ""


def messages_to_context(
    messages: Iterable[dict[str, Any]], trusted_tools: frozenset[str] = frozenset()
) -> list[dict[str, str]]:
    names: dict[str, str] = {}
    context: list[dict[str, str]] = []
    for message in messages:
        for block in message.get("content", []):
            if "toolUse" in block:
                names[block["toolUse"]["toolUseId"]] = block["toolUse"]["name"]
            elif "toolResult" in block:
                result = block["toolResult"]
                text = "\n".join(filter(None, map(block_text, result.get("content", []))))
                tool = names.get(result.get("toolUseId", ""), "")
                origin = "store" if tool in trusted_tools else "untrusted"
                context.append({"origin": origin, "text": text[:MAX_TEXT]})
            elif message.get("role") == "user" and block_text(block):
                context.append({"origin": "user", "text": block_text(block)[:MAX_TEXT]})
    return [segment for segment in context if segment["text"]][-MAX_SEGMENTS:]


class AgentZeroGuardHook(HookProvider):
    def __init__(
        self,
        guard: AgentZeroGuard,
        subject: str,
        trusted_tools: Iterable[str] = (),
        owner_of: Callable[[str, dict[str, Any]], dict[str, str]] | None = None,
    ) -> None:
        self.guard = guard
        self.subject = subject
        self.trusted_tools = frozenset(trusted_tools)
        self.owner_of = owner_of
        self.pending: dict[str, dict[str, Any]] = {}
        self.last_learned: dict[str, Any] = {}

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeToolCallEvent, self.before_tool)
        registry.add_callback(AfterToolCallEvent, self.after_tool)

    def before_tool(self, event: BeforeToolCallEvent) -> None:
        tool = event.tool_use["name"]
        arguments = dict(event.tool_use.get("input") or {})
        owners = self.owner_of(tool, arguments) if self.owner_of else {}
        context = messages_to_context(event.agent.messages, self.trusted_tools)
        try:
            decision = self.guard.check(self.subject, tool, arguments, context, owners)
        except Exception:
            decision = {"allowed": False, "rule_id": "guard_unreachable", "reason": "Guard caído."}
        learned = decision.get("learned")
        if learned:
            violated = (learned.get("report") or {}).get("violated", [])
            self.last_learned = {"violations": violated, "policy": learned}
        if decision.get("allowed"):
            self.pending[event.tool_use["toolUseId"]] = {
                "call_id": decision["call_id"],
                "owners": owners,
            }
            return
        reason = decision.get("reason") or decision.get("rule_id")
        event.cancel_tool = f"Denegado por Agent Zero: {reason} ({decision.get('rule_id')})"

    def after_tool(self, event: AfterToolCallEvent) -> None:
        call = self.pending.pop(event.tool_use["toolUseId"], None)
        if call is None or event.result.get("status") == "error":
            return
        self.guard.report(call["call_id"], call["owners"])
