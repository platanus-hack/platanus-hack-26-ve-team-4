from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

SERVER = Path(__file__).resolve().parent.parent / "mcp_banco_server.py"


def converse(messages: list[dict]) -> list[dict]:
    payload = "".join(json.dumps(message) + "\n" for message in messages)
    done = subprocess.run(
        [sys.executable, str(SERVER)], input=payload, capture_output=True, text=True, timeout=20
    )
    return [json.loads(line) for line in done.stdout.splitlines()]


class BancoServerTest(unittest.TestCase):
    def test_initialize_list_and_call(self) -> None:
        replies = converse(
            [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "consultar_saldo", "arguments": {"cuenta": "CTA-1"}},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {"name": "leer_correo", "arguments": {"carpeta": "entrada"}},
                },
            ]
        )
        self.assertEqual([reply["id"] for reply in replies], [1, 2, 3, 4])
        self.assertIn("tools", replies[0]["result"]["capabilities"])
        names = {tool["name"] for tool in replies[1]["result"]["tools"]}
        self.assertEqual(names, {"consultar_saldo", "transferir", "leer_correo"})
        self.assertIn("1200 USD", replies[2]["result"]["content"][0]["text"])
        self.assertIn("BEN-EXTERNO", replies[3]["result"]["content"][0]["text"])

    def test_unknown_method_and_tool(self) -> None:
        replies = converse(
            [
                {"jsonrpc": "2.0", "id": 1, "method": "nada"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "x"}},
            ]
        )
        self.assertEqual(replies[0]["error"]["code"], -32601)
        self.assertTrue(replies[1]["result"]["isError"])


if __name__ == "__main__":
    unittest.main()
