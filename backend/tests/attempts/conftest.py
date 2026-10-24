import time
from collections.abc import Callable, Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from agent_zero.attempts.execution import (
    ARENA_ATTEMPT_HANDLER,
    ArenaTarget,
    ArenaWiring,
    EvaluationInput,
)
from agent_zero.attempts.models import AttemptOutcome
from agent_zero.config import Settings
from agent_zero.main import create_app
from agent_zero.runtime.handlers import StepContext
from agent_zero.runtime.step_results import Complete, Fail, StepResult, Wait
from agent_zero.victim.manifest import SUPPORT_AGENT_ID, support_manifest

OPERATOR = {"X-Operator-Secret": "secreto-de-operador-de-prueba"}


class FakeArenaHandler:
    """Ocupa el lugar de la víctima (#5): responde, falla o se queda esperando."""

    name = ARENA_ATTEMPT_HANDLER

    def __init__(self) -> None:
        self.mode = "reply"
        self.inputs: list[dict[str, Any]] = []

    async def step(self, context: StepContext) -> StepResult:
        self.inputs.append(dict(context.input))
        if self.mode == "fail":
            return Fail(reason="la víctima no respondió")
        if self.mode == "wait":
            return Wait(until=context.now + timedelta(hours=1))
        return Complete(output={"reply": f"Recibido: {context.input['messages'][-1]}"})


class FakeEvaluator:
    """Ocupa el lugar de los oráculos (#8) con un veredicto fijo."""

    def __init__(self, verdict: AttemptOutcome) -> None:
        self.verdict = verdict
        self.seen: list[EvaluationInput] = []

    async def evaluate(self, attempt: EvaluationInput) -> AttemptOutcome:
        self.seen.append(attempt)
        return self.verdict


class Arena:
    def __init__(self, client: TestClient, handler: FakeArenaHandler) -> None:
        self.client = client
        self.handler = handler
        self.wiring: ArenaWiring = client.app.state.arena  # type: ignore[attr-defined]

    def connect_victim(self, version: str = "1.0.0") -> None:
        self.wiring.target = ArenaTarget(agent_id=SUPPORT_AGENT_ID, agent_version=version)

    def session(self, alias: str = "neo") -> dict[str, str]:
        body = {"alias": alias, "accepted_rules": True}
        token = self.client.post("/api/sessions", json=body).json()["token"]
        return {"Authorization": f"Bearer {token}"}

    def submit(self, auth: dict[str, str], key: str, **body: Any) -> Any:
        payload = {"idempotency_key": key, **(body or {"message": "Consulta mi pedido"})}
        return self.client.post("/api/attempts", json=payload, headers=auth)

    def wait_until(self, check: Callable[[], bool], timeout: float = 5.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if check():
                return
            time.sleep(0.02)
        raise AssertionError("La condición no se cumplió a tiempo.")

    def settle(self, attempt_id: str, auth: dict[str, str]) -> dict[str, Any]:
        def done() -> bool:
            view = self.client.get(f"/api/attempts/{attempt_id}", headers=auth).json()
            return view["status"] in ("evaluated", "inconclusive")

        self.wait_until(done)
        result: dict[str, Any] = self.client.get(
            f"/api/operator/attempts/{attempt_id}", headers=OPERATOR
        ).json()
        return result


@pytest.fixture
def arena_settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path,
        environment="test",
        operator_secret=OPERATOR["X-Operator-Secret"],
        runtime_poll_seconds=0.02,
        attempt_min_interval_seconds=0,
    )


@pytest.fixture
def arena(arena_settings: Settings) -> Iterator[Arena]:
    handler = FakeArenaHandler()
    with TestClient(create_app(arena_settings)) as client:
        client.app.state.handler_registry.register(handler)  # type: ignore[attr-defined]
        manifest = support_manifest().model_dump(mode="json")
        assert client.post("/api/registry/agents", json=manifest, headers=OPERATOR).is_success
        approve = f"/api/registry/agents/{SUPPORT_AGENT_ID}/versions/1.0.0/approve"
        assert client.post(approve, json={"approved_by": "test"}, headers=OPERATOR).is_success
        yield Arena(client, handler)
