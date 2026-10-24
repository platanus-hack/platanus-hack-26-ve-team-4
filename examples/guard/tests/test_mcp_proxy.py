from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

from examples.guard.tests.fake_guard import FakeGuard

GUARD_DIR = Path(__file__).resolve().parent.parent
ROOT = GUARD_DIR.parent.parent
PROXY = GUARD_DIR / "mcp_proxy.py"
SERVER = GUARD_DIR / "mcp_banco_server.py"


def call(identifier: int, name: str, **arguments: Any) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": identifier,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }


def run_proxy(url: str, messages: list[dict], *extra: str) -> list[dict]:
    command = [
        sys.executable,
        str(PROXY),
        "--guard",
        url,
        "--contract",
        "banco",
        "--subject",
        "ana",
        *extra,
        "--",
        sys.executable,
        str(SERVER),
    ]
    payload = "".join(json.dumps(message) + "\n" for message in messages)
    env = dict(os.environ, AGENT_ZERO_GUARD_API_KEY="clave-prueba")
    done = subprocess.run(
        command, input=payload, capture_output=True, text=True, timeout=30, env=env, cwd=str(ROOT)
    )
    return [json.loads(line) for line in done.stdout.splitlines()]


def deny_transfers(body: dict[str, Any]) -> dict[str, Any]:
    if body["tool"] == "transferir":
        return {"allowed": False, "rule_id": "invariant:tope", "reason": "Tope superado."}
    return {"allowed": True}


class McpProxyTest(unittest.TestCase):
    def test_relays_protocol_and_reports_effects(self) -> None:
        with FakeGuard() as guard:
            replies = run_proxy(
                guard.url,
                [
                    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                    call(3, "consultar_saldo", cuenta="CTA-1"),
                ],
            )
        self.assertEqual([reply["id"] for reply in replies], [1, 2, 3])
        self.assertFalse(replies[2]["result"]["isError"])
        self.assertEqual(len(guard.checks), 1)
        self.assertEqual(guard.checks[0]["owners"], {})
        self.assertEqual(guard.checks[0]["subject"], "ana")
        self.assertEqual(guard.effects, [{"call_id": "gc-1", "owners": {}}])
        self.assertEqual(guard.headers[0], "clave-prueba")

    def test_denial_is_not_forwarded(self) -> None:
        with FakeGuard(deny_transfers) as guard:
            replies = run_proxy(
                guard.url,
                [call(1, "transferir", cuenta="CTA-1", destino="X", monto=9, concepto="c")],
            )
        result = replies[0]["result"]
        self.assertTrue(result["isError"])
        text = result["content"][0]["text"]
        self.assertTrue(text.startswith("Denegado por Agent Zero: Tope superado."))
        self.assertEqual(guard.effects, [])

    def test_context_labels_untrusted_and_trusted(self) -> None:
        with FakeGuard() as guard:
            run_proxy(
                guard.url,
                [
                    call(1, "leer_correo", carpeta="entrada"),
                    call(2, "consultar_saldo", cuenta="CTA-1"),
                    call(3, "leer_correo", carpeta="x"),
                ],
                "--trusted-tool",
                "consultar_saldo",
            )
        self.assertEqual(guard.checks[0]["context"], [])
        self.assertEqual([c["origin"] for c in guard.checks[1]["context"]], ["untrusted"])
        origins = [c["origin"] for c in guard.checks[2]["context"]]
        self.assertEqual(origins, ["untrusted", "store"])
        self.assertIn("BEN-EXTERNO", guard.checks[1]["context"][0]["text"])

    def test_fail_closed_when_guard_is_down(self) -> None:
        replies = run_proxy("http://127.0.0.1:9", [call(1, "consultar_saldo", cuenta="CTA-1")])
        self.assertTrue(replies[0]["result"]["isError"])
        self.assertIn("guard_unreachable", replies[0]["result"]["content"][0]["text"])

    def test_owners_module(self) -> None:
        module = GUARD_DIR / "tests" / "owners_fixture.py"
        module.write_text("def owners(tool, arguments):\n    return {'cuenta': 'ana'}\n")
        self.addCleanup(module.unlink)
        with FakeGuard() as guard:
            run_proxy(
                guard.url,
                [call(1, "consultar_saldo", cuenta="CTA-1")],
                "--owners-module",
                "examples.guard.tests.owners_fixture:owners",
            )
        self.assertEqual(guard.checks[0]["owners"], {"cuenta": "ana"})
        self.assertEqual(guard.effects[0]["owners"], {"cuenta": "ana"})


if __name__ == "__main__":
    unittest.main()
