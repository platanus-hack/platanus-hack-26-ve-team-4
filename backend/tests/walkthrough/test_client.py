from typing import Any

import pytest

from agent_zero.walkthrough.client import FleetClient, RunTimeoutError


class Response:
    def __init__(self, status_code: int, body: Any) -> None:
        self.status_code = status_code
        self._body = body

    def json(self) -> Any:
        return self._body


class ScriptedHttp:
    def __init__(self, statuses: list[str]) -> None:
        self.statuses = statuses
        self.headers: list[dict[str, str]] = []

    def get(self, url: str, **kwargs: Any) -> Response:
        self.headers.append(kwargs["headers"])
        return Response(
            200, {"status": self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]}
        )

    def post(self, url: str, **kwargs: Any) -> Response:
        return Response(202, {"run_id": "run-1"})


def test_wait_for_collects_every_status_until_terminal() -> None:
    http = ScriptedHttp(["queued", "waiting", "succeeded"])
    client = FleetClient(http, "secreto", sleep=lambda _: None)

    run, seen = client.wait_for(client.enqueue("agente", "handler", {}), 10)

    assert run["status"] == "succeeded"
    assert seen == {"queued", "waiting", "succeeded"}
    assert http.headers[0] == {"x-operator-secret": "secreto"}


def test_wait_for_gives_up_after_the_timeout() -> None:
    client = FleetClient(ScriptedHttp(["running"]), "secreto", poll_seconds=1, sleep=lambda _: None)

    with pytest.raises(RunTimeoutError):
        client.wait_for("run-1", 3)
