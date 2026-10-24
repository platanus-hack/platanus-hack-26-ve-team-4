from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

Context = list[dict[str, str]]


class ToolDeniedError(PermissionError):
    def __init__(self, decision: dict[str, Any]) -> None:
        super().__init__(decision.get("reason") or decision.get("rule_id"))
        self.decision = decision


@dataclass
class AgentZeroGuard:
    base_url: str
    contract_id: str
    api_key: str
    timeout: float = 5.0
    verdicts: list[dict[str, Any]] = field(default_factory=list)
    last_learned: dict[str, Any] = field(default_factory=dict)

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

    def check(
        self,
        subject: str,
        tool: str,
        arguments: dict[str, Any],
        context: Context,
        owners: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        body = {
            "subject": subject,
            "tool": tool,
            "arguments": arguments,
            "context": context,
            "owners": owners or {},
        }
        try:
            return self._post("check", body)
        except (urllib.error.URLError, TimeoutError):
            return {"allowed": False, "rule_id": "guard_unreachable", "reason": "Guard caído."}

    def report(self, call_id: str, owners: dict[str, str] | None = None) -> dict[str, Any]:
        verdict = self._post("effects", {"call_id": call_id, "owners": owners or {}})
        self.verdicts.append(verdict)
        return verdict

    def wrap(
        self,
        tool: str,
        function: Callable[..., Any],
        owner_of: Callable[[dict[str, Any]], dict[str, str]] | None = None,
    ) -> Callable[..., Any]:
        def guarded(subject: str, context: Context, **arguments: Any) -> Any:
            owners = owner_of(arguments) if owner_of else {}
            decision = self.check(subject, tool, arguments, context, owners)
            if decision.get("learned"):
                policy = decision["learned"]
                self.last_learned = {"violations": policy["report"]["violated"], "policy": policy}
            if not decision["allowed"]:
                raise ToolDeniedError(decision)
            result = function(**arguments)
            self.report(decision["call_id"], owners)
            return result

        return guarded
