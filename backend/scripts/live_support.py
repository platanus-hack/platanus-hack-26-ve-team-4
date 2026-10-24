"""Isolated helpers for the explicit, budgeted live verification command."""

import hashlib
import ipaddress
import json
import socket
import time
import urllib.request
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_zero.config import Settings
from agent_zero.evals.provenance import source_revision


class LiveVerificationError(RuntimeError):
    pass


@contextmanager
def diagnostic_dns(enabled: bool) -> Iterator[dict[str, Any]]:
    """Cloudflare DoH JSON: TLS is verified, only this process and hostname change."""
    if not enabled:
        yield {"enabled": False}
        return
    hostname = "api.anthropic.com"
    url = f"https://1.1.1.1/dns-query?name={hostname}&type=A&fresh={time.time_ns()}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/dns-json",
            "Cache-Control": "no-cache",
        },
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=15) as response:
        payload = json.load(response)
    answers = [
        record
        for record in payload.get("Answer", [])
        if record.get("type") == 1
        and record.get("TTL", 0) > 0
        and ipaddress.ip_address(record["data"]).is_global
    ]
    if payload.get("Status") != 0 or not answers:
        raise LiveVerificationError("El diagnóstico DoH no obtuvo una dirección pública vigente.")
    original = socket.getaddrinfo

    def resolve(host: Any, *arguments: Any, **keywords: Any) -> Any:
        name = host.decode() if isinstance(host, bytes) else host
        target = (
            answers[0]["data"] if isinstance(name, str) and name.rstrip(".") == hostname else host
        )
        return original(target, *arguments, **keywords)

    socket.getaddrinfo = resolve
    try:
        yield {
            "enabled": True,
            "hostname": hostname,
            "resolver": "https://1.1.1.1/dns-query",
            "answers": answers,
            "tls_hostname_verification": True,
            "scope": "process_only",
        }
    finally:
        socket.getaddrinfo = original


class LiveHarness:
    def __init__(self, client: TestClient, settings: Settings) -> None:
        self.client, self.settings = client, settings
        self.artifact: dict[str, Any] = {
            **source_revision(),
            "llm_mode": "live",
            "checks": {},
            "errors": [],
            "configured_model": settings.llm_model,
            "configured_role_models": settings.llm_role_models,
            "budget_usd": settings.llm_daily_usd_limit,
            "call_limit": settings.llm_daily_call_limit,
            "attempts": [],
        }

    def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        token: str | None = None,
    ) -> Any:
        headers = (
            {"Authorization": f"Bearer {token}"}
            if token
            else {
                "X-Operator-Secret": self.settings.operator_secret.get_secret_value(),
            }
        )
        response = self.client.request(method, path, headers=headers, json=body)
        if response.status_code >= 400:
            raise LiveVerificationError(f"{method} {path}: HTTP {response.status_code}")
        return response.json()

    def wait(self, phase: str, check: Callable[[], Any]) -> Any:
        print(f"LIVE {phase}: esperando evidencia", flush=True)
        deadline, next_update = time.monotonic() + 60, time.monotonic() + 10
        while time.monotonic() < deadline:
            result = check()
            if result is not None:
                return result
            if time.monotonic() >= next_update:
                print(f"LIVE {phase}: sigue pendiente", flush=True)
                next_update += 10
            time.sleep(0.1)
        raise LiveVerificationError(f"La fase {phase} excedió 60 segundos.")

    def require(self, condition: bool, phase: str) -> None:
        self.artifact["checks"][phase] = bool(condition)
        if not condition:
            raise LiveVerificationError(f"La evidencia no satisface {phase}.")
        print(f"LIVE {phase}: verificado", flush=True)

    def attempt(self, session: dict[str, Any], message: str, key: str) -> dict[str, Any]:
        queued = self.request(
            "POST",
            "/api/attempts",
            {"message": message, "idempotency_key": key},
            token=session["token"],
        )
        return self.terminal(queued["id"])

    def terminal(self, attempt_id: str) -> dict[str, Any]:
        def read() -> Any:
            value = self.request("GET", f"/api/operator/attempts/{attempt_id}")
            return value if value["outcome"] is not None else None

        result: dict[str, Any] = self.wait(f"intento {attempt_id}", read)
        self.artifact["attempts"].append(result)
        return result

    def active(self) -> dict[str, Any]:
        return next(
            row
            for row in self.request("GET", "/api/operator/policies")
            if row["status"] == "active"
        )

    def collect(self) -> None:
        self.artifact["policies"] = self.request("GET", "/api/operator/policies")
        self.artifact["findings"] = self.request("GET", "/api/operator/findings")
        self.artifact["campaigns"] = self.request("GET", "/api/operator/campaigns")
        self.artifact["attempts"] = [
            self.request("GET", f"/api/operator/attempts/{row['id']}")
            for row in self.request("GET", "/api/operator/attempts")
        ]

    def ledger(self) -> None:
        app = cast(FastAPI, self.client.app)
        records = app.state.llm.ledger.records()
        self.artifact["llm_ledger"] = [row.model_dump(mode="json") for row in records]
        self.artifact["origins"] = sorted({row.origin.value for row in records})
        self.artifact["measured_calls"] = sum(row.measured for row in records)
        self.artifact["calls"] = len(records)
        self.artifact["known_cost_usd"] = sum(row.cost.total_usd for row in records if row.cost)
        self.artifact["unpriced_calls"] = sum(row.cost is None for row in records)
        self.artifact["live_execution_verified"] = bool(records) and all(
            row.measured for row in records
        )
        self.artifact["within_budget"] = (
            len(records) <= self.settings.llm_daily_call_limit
            and self.artifact["known_cost_usd"] <= self.settings.llm_daily_usd_limit
        )


def export_artifact(payload: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    output.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    output.with_suffix(output.suffix + ".sha256").write_text(
        f"{digest}  {output.name}\n", encoding="utf-8"
    )
