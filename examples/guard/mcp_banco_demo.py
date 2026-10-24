from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


class McpSession:
    def __init__(self, command: list[str], env: dict[str, str]) -> None:
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            env=env,
            cwd=str(HERE),
        )
        self.counter = 0

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self.counter += 1
        message = {"jsonrpc": "2.0", "id": self.counter, "method": method, "params": params}
        assert self.process.stdin is not None and self.process.stdout is not None
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()
        reply: dict[str, Any] = json.loads(self.process.stdout.readline())
        return reply

    def call(self, tool: str, **arguments: Any) -> str:
        reply = self.request("tools/call", {"name": tool, "arguments": arguments})
        result = reply["result"]
        status = "DENEGADA " if result["isError"] else "EJECUTADA"
        return f"{status} {tool} {arguments}\n           -> {result['content'][0]['text'][:110]}"

    def close(self) -> None:
        assert self.process.stdin is not None
        self.process.stdin.close()
        self.process.wait(timeout=10)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--contract", default="banco-transferencias")
    parser.add_argument("--subject", default="ana")
    args = parser.parse_args()
    key = os.environ.get("AGENT_ZERO_GUARD_API_KEY", "change-me-guard")
    env = dict(os.environ, AGENT_ZERO_GUARD_API_KEY=key, BANCO_TITULAR=args.subject)
    command = [
        sys.executable, "mcp_proxy.py", "--guard", args.url, "--contract", args.contract,
        "--subject", args.subject, "--trusted-tool", "consultar_saldo",
        "--owners-module", "banco_owners:owners", "--",
        sys.executable, "mcp_banco_server.py",
    ]
    session = McpSession(command, env)
    session.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}})
    transfer = {"cuenta": "CTA-1", "concepto": "pago"}
    print("0. Saldo propio (herramienta de confianza)")
    print(session.call("consultar_saldo", cuenta="CTA-1"))
    print("1. Leer el correo (contenido no confiable)")
    print(session.call("leer_correo", carpeta="entrada"))
    print("2. Transferencia inyectada de 900 a un beneficiario externo")
    print(session.call("transferir", destino="BEN-EXTERNO", monto=900, **transfer))
    print("3. Transferencia de 40 con monto y destino tomados del correo")
    print(session.call("transferir", destino="BEN-AHORRO", monto=40, **transfer))
    print("4. Transferencia legitima: valores que no salen del correo")
    print(session.call("transferir", destino="BEN-ALQUILER", monto=450, **transfer))
    session.close()


if __name__ == "__main__":
    main()
