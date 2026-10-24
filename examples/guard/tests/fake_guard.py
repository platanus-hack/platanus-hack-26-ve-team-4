from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable

Decider = Callable[[dict[str, Any]], dict[str, Any]]


def allow_all(body: dict[str, Any]) -> dict[str, Any]:
    return {"allowed": True}


class FakeGuard:
    def __init__(self, decider: Decider = allow_all) -> None:
        self.decider = decider
        self.checks: list[dict[str, Any]] = []
        self.effects: list[dict[str, Any]] = []
        self.headers: list[str] = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                body = json.loads(self.rfile.read(int(self.headers["content-length"])))
                owner.headers.append(self.headers.get("x-guard-key", ""))
                if self.path.endswith("/check"):
                    owner.checks.append(body)
                    reply = {"call_id": f"gc-{len(owner.checks)}", "policy_version": 0}
                    reply.update(owner.decider(body))
                else:
                    owner.effects.append(body)
                    reply = {"call_id": body["call_id"], "violations": []}
                payload = json.dumps(reply).encode()
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args: Any) -> None:
                return

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> FakeGuard:
        self.thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.server.shutdown()
        self.server.server_close()
