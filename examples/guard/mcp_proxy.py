from __future__ import annotations

import argparse
import importlib
import json
import os
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from typing import Any, Callable, Optional

MAX_SEGMENTS = 200
MAX_TEXT = 20000
SETTLE_SECONDS = 30.0


class GuardClient:
    def __init__(self, base_url: str, contract_id: str, api_key: str, timeout: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.contract_id = contract_id
        self.api_key = api_key
        self.timeout = timeout

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}/api/guard/{self.contract_id}/{path}",
            data=json.dumps(body).encode(),
            headers={"content-type": "application/json", "x-guard-key": self.api_key},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            result: dict[str, Any] = json.load(response)
            return result

    def check(self, body: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._post("check", body)
        except (urllib.error.URLError, TimeoutError, ValueError, OSError):
            return {"allowed": False, "rule_id": "guard_unreachable", "reason": "Guard caído."}

    def report(self, call_id: str, owners: dict[str, str]) -> dict[str, Any]:
        return self._post("effects", {"call_id": call_id, "owners": owners})


def load_owners(spec: Optional[str]) -> Callable[[str, dict[str, Any]], dict[str, str]]:
    if not spec:
        return lambda tool, arguments: {}
    module_name, _, function_name = spec.partition(":")
    sys.path.insert(0, os.getcwd())
    function: Callable[[str, dict[str, Any]], dict[str, str]] = getattr(
        importlib.import_module(module_name), function_name
    )
    return function


def result_text(result: dict[str, Any]) -> str:
    parts = [
        block.get("text", "")
        for block in result.get("content", [])
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    return "\n".join(parts)


def denial(request_id: Any, decision: dict[str, Any]) -> dict[str, Any]:
    reason = decision.get("reason") or decision.get("rule_id") or "sin motivo"
    text = f"Denegado por Agent Zero: {reason} ({decision.get('rule_id')})"
    result = {"content": [{"type": "text", "text": text}], "isError": True}
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


class Proxy:
    def __init__(
        self,
        guard: GuardClient,
        subject: str,
        trusted_tools: list[str],
        owners_of: Callable[[str, dict[str, Any]], dict[str, str]],
        server_command: list[str],
    ) -> None:
        self.guard = guard
        self.subject = subject
        self.trusted = set(trusted_tools)
        self.owners_of = owners_of
        self.context: list[dict[str, str]] = []
        self.pending: dict[Any, dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.settled = threading.Condition()
        self.server = subprocess.Popen(
            server_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )

    def write_client(self, message: dict[str, Any]) -> None:
        with self.lock:
            sys.stdout.write(json.dumps(message) + "\n")
            sys.stdout.flush()

    def write_server(self, line: str) -> None:
        assert self.server.stdin is not None
        self.server.stdin.write(line if line.endswith("\n") else line + "\n")
        self.server.stdin.flush()

    def handle_call(self, message: dict[str, Any], line: str) -> None:
        with self.settled:
            self.settled.wait_for(lambda: not self.pending, timeout=SETTLE_SECONDS)
        params = message.get("params") or {}
        tool = str(params.get("name", ""))
        arguments = params.get("arguments") or {}
        owners = self.owners_of(tool, arguments)
        body = {
            "subject": self.subject,
            "tool": tool,
            "arguments": arguments,
            "context": list(self.context[-MAX_SEGMENTS:]),
            "owners": owners,
        }
        decision = self.guard.check(body)
        learned = decision.get("learned")
        if learned:
            violated = (learned.get("report") or {}).get("violated")
            sys.stderr.write(f"[agent-zero] política aprendida v{learned.get('version')}: {violated}\n")
        if not decision.get("allowed"):
            self.write_client(denial(message.get("id"), decision))
            return
        with self.settled:
            self.pending[message.get("id")] = {
                "tool": tool,
                "call_id": decision["call_id"],
                "owners": owners,
            }
        self.write_server(line)

    def record(self, tool: str, result: dict[str, Any]) -> None:
        text = result_text(result)
        if text:
            origin = "store" if tool in self.trusted else "untrusted"
            self.context.append({"origin": origin, "text": text[:MAX_TEXT]})

    def pump_server(self) -> None:
        assert self.server.stdout is not None
        for line in self.server.stdout:
            try:
                message = json.loads(line)
            except ValueError:
                message = {}
            with self.settled:
                call = self.pending.pop(message.get("id"), None) if "id" in message else None
                if call and "result" in message:
                    self.record(call["tool"], message["result"])
                self.settled.notify_all()
            with self.lock:
                sys.stdout.write(line if line.endswith("\n") else line + "\n")
                sys.stdout.flush()
            if call and "result" in message:
                try:
                    self.guard.report(call["call_id"], call["owners"])
                except (urllib.error.URLError, OSError, ValueError) as failure:
                    sys.stderr.write(f"[agent-zero] effects falló: {failure}\n")

    def run(self) -> int:
        pump = threading.Thread(target=self.pump_server, daemon=True)
        pump.start()
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                message = json.loads(line)
            except ValueError:
                self.write_server(line)
                continue
            if isinstance(message, dict) and message.get("method") == "tools/call" and "id" in message:
                self.handle_call(message, line)
            else:
                self.write_server(line)
        assert self.server.stdin is not None
        self.server.stdin.close()
        pump.join()
        return self.server.wait()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Proxy MCP con Agent Zero Guard")
    parser.add_argument("--guard", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--trusted-tool", action="append", default=[])
    parser.add_argument("--owners-module")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    args.command = [part for index, part in enumerate(args.command) if index or part != "--"]
    if not args.command:
        parser.error("falta el comando del servidor MCP después de --")
    return args


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    guard = GuardClient(args.guard, args.contract, os.environ.get("AGENT_ZERO_GUARD_API_KEY", ""))
    proxy = Proxy(guard, args.subject, args.trusted_tool, load_owners(args.owners_module), args.command)
    return proxy.run()


if __name__ == "__main__":
    sys.exit(main())
