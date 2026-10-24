from __future__ import annotations

import unittest
from typing import Any

from examples.guard.tests.fake_guard import FakeGuard

try:
    from examples.guard.agent_zero_guard import AgentZeroGuard
    from examples.guard.strands_guard import AgentZeroGuardHook, messages_to_context
    from strands.hooks import AfterToolCallEvent, BeforeToolCallEvent, HookRegistry

    HAS_STRANDS = True
except ImportError:
    HAS_STRANDS = False


class FakeAgent:
    def __init__(self, messages: list[dict[str, Any]]) -> None:
        self.messages = messages


def tool_use(identifier: str, name: str) -> dict[str, Any]:
    return {"role": "assistant", "content": [{"toolUse": {"toolUseId": identifier, "name": name, "input": {}}}]}


def tool_result(identifier: str, content: dict[str, Any]) -> dict[str, Any]:
    result = {"toolUseId": identifier, "status": "success", "content": [content]}
    return {"role": "user", "content": [{"toolResult": result}]}


MESSAGES = [
    {"role": "user", "content": [{"text": "Resume mi correo"}]},
    tool_use("t1", "leer_correo"),
    tool_result("t1", {"text": "correo"}),
    tool_use("t2", "consultar_saldo"),
    tool_result("t2", {"json": {"saldo": 5}}),
]


@unittest.skipUnless(HAS_STRANDS, "strands no está instalado")
class StrandsGuardTest(unittest.TestCase):
    def test_context_labels(self) -> None:
        context = messages_to_context(MESSAGES, frozenset({"consultar_saldo"}))
        self.assertEqual(
            context,
            [
                {"origin": "user", "text": "Resume mi correo"},
                {"origin": "untrusted", "text": "correo"},
                {"origin": "store", "text": '{"saldo": 5}'},
            ],
        )

    def build(self, url: str) -> tuple[Any, Any]:
        client = AgentZeroGuard(url, "banco", "k", timeout=2)
        hook = AgentZeroGuardHook(client, "ana", trusted_tools=["consultar_saldo"])
        registry = HookRegistry()
        hook.register_hooks(registry)
        return hook, registry

    def before(self, registry: Any) -> Any:
        use = {"toolUseId": "t9", "name": "transferir", "input": {"monto": 900}}
        event = BeforeToolCallEvent(
            agent=FakeAgent(MESSAGES), selected_tool=None, tool_use=use, invocation_state={}
        )
        registry.invoke_callbacks(event)
        return event

    def after(self, registry: Any, event: Any, status: str) -> None:
        result = {"toolUseId": "t9", "status": status, "content": [{"text": "ok"}]}
        registry.invoke_callbacks(
            AfterToolCallEvent(
                agent=FakeAgent(MESSAGES),
                selected_tool=None,
                tool_use=event.tool_use,
                invocation_state={},
                result=result,
            )
        )

    def test_allow_then_report(self) -> None:
        with FakeGuard() as guard:
            hook, registry = self.build(guard.url)
            event = self.before(registry)
            self.assertFalse(event.cancel_tool)
            self.after(registry, event, "success")
        self.assertEqual(guard.checks[0]["arguments"], {"monto": 900})
        self.assertEqual(len(guard.checks[0]["context"]), 3)
        self.assertEqual(guard.effects, [{"call_id": "gc-1", "owners": {}}])

    def test_deny_cancels_and_does_not_report(self) -> None:
        learned = {"version": 1, "report": {"violated": ["tope"]}}
        deny = {"allowed": False, "rule_id": "invariant:tope", "reason": "Tope.", "learned": learned}
        with FakeGuard(lambda body: deny) as guard:
            hook, registry = self.build(guard.url)
            event = self.before(registry)
            self.after(registry, event, "error")
        self.assertIn("Denegado por Agent Zero: Tope.", event.cancel_tool)
        self.assertEqual(guard.effects, [])
        self.assertEqual(hook.last_learned["violations"], ["tope"])

    def test_fail_closed(self) -> None:
        hook, registry = self.build("http://127.0.0.1:9")
        event = self.before(registry)
        self.assertIn("guard_unreachable", event.cancel_tool)


if __name__ == "__main__":
    unittest.main()
