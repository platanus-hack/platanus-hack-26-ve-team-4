from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_zero.arena.core import ProductCore
from agent_zero.config import Settings
from agent_zero.events.broker import EventBroker
from agent_zero.events.event_store import EventStore
from agent_zero.events.models import EventType
from agent_zero.llm.models import ModelRole
from agent_zero.main import create_app
from tests.arena.support import OPERATOR, ScenarioPlayback, foreign_order, join, send, wait_attempt


@pytest.mark.requirement("CORE-05")
def test_queued_attempt_and_evidence_survive_application_restart(settings: Settings) -> None:
    configured = settings.model_copy(
        update={"runtime_poll_seconds": 0.005, "arena_auto_patch": False}
    )
    with TestClient(
        create_app(configured, {role: ScenarioPlayback() for role in ModelRole})
    ) as client:
        session = join(client)
        core: ProductCore = cast(FastAPI, client.app).state.core
        assert client.portal is not None
        client.portal.call(core.fleet.worker.stop)
        queued = send(client, session, f"Consulta {foreign_order(session)}.")
        events_before = client.get(
            f"/api/operator/attempts/{queued['id']}", headers=OPERATOR
        ).json()["events"]
        last_id = events_before[-1]["id"]
    with TestClient(
        create_app(configured, {role: ScenarioPlayback() for role in ModelRole})
    ) as client:
        result = wait_attempt(client, queued["id"])
        assert result["outcome"] == "confirmed_violation", result
        assert result["events"][0]["id"] == last_id
        assert result["events"][-1]["id"] > last_id
        private = client.get(
            f"/api/attempts/{queued['id']}", headers={"Authorization": f"Bearer {session['token']}"}
        )
        assert private.status_code == 200
        assert private.json()["outcome"] == "apparent_success"
        audit = client.get("/api/fleet/audit", headers=OPERATOR).json()
        assert audit["verification"]["ok"] is True


def test_public_history_survives_eviction_without_private_fields(manual_client: TestClient) -> None:
    core: ProductCore = cast(FastAPI, manual_client.app).state.core

    async def history() -> list[int]:
        broker = EventBroker(history_size=1)
        events = EventStore(core.fleet, broker)
        await events.restore()
        for index in range(3):
            await events.public(EventType.ATTEMPT_QUEUED, 0, status=str(index), route="honeypot")
        async with broker.subscribe(after_id=0) as queue:
            received = [queue.get_nowait() for _ in range(queue.qsize())]
            assert all("route" not in event.data for event in received)
            return [event.id for event in received]

    assert manual_client.portal is not None
    ids = manual_client.portal.call(history)
    assert ids == sorted(ids)
    assert len(ids) == 3
