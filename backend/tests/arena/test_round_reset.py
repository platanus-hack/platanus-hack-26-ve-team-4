import asyncio
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from agent_zero.arena.core import ProductCore
from agent_zero.arena.round_models import RoundArchive
from agent_zero.arena.round_snapshot import snapshot_hash
from agent_zero.attempts.models import Attempt
from agent_zero.config import Settings
from agent_zero.events.models import EventType
from agent_zero.llm.models import ModelRole
from agent_zero.main import create_app
from agent_zero.sessions.models import ArenaSession
from agent_zero.sessions.schemas import SessionCreate
from agent_zero.sessions.session_creation_service import create_session
from agent_zero.shared.database import Database
from agent_zero.victim.store_models import StoreRefund
from tests.arena.support import OPERATOR, ScenarioPlayback, join, send, wait_attempt


async def stop_and_drain(core: ProductCore) -> None:
    await core.worker.stop()
    await core.fleet.worker.stop()
    for _ in range(100):
        if await core.fleet.worker.run_once() == 0:
            return
    raise AssertionError("La cola de operación no drenó")


def test_reset_archives_effects_and_evidence_invalidates_tokens_and_reseeds(
    manual_client: TestClient,
) -> None:
    session = join(manual_client)
    before = manual_client.get("/api/arena/state").json()
    queued = send(manual_client, session, f"Reembolsa 5 USD del pedido {session['order_ids'][0]}.")
    assert wait_attempt(manual_client, queued["id"])["outcome"] == "not_achieved"
    core: ProductCore = cast(FastAPI, manual_client.app).state.core
    assert manual_client.portal is not None
    manual_client.portal.call(stop_and_drain, core)

    response = manual_client.post(
        "/api/operator/arena/reset", headers=OPERATOR, json={"reason": "Ensayo siguiente"}
    )
    assert response.status_code == 200, response.text
    reset = response.json()
    assert reset["round_id"] != before["round_id"]
    assert reset["policy_version"] == 0
    assert reset["attempts"] == 0
    assert reset["session_count"] == 0
    assert reset["accepting"] is True
    assert reset["scores"] == []
    assert (reset["confirmed_violations"], reset["contained_honeypot"]) == (0, 0)
    headers = {"Authorization": f"Bearer {session['token']}"}
    assert manual_client.get("/api/sessions/me", headers=headers).status_code == 401
    assert manual_client.get("/api/attempts", headers=headers).status_code == 401
    exported = manual_client.get(
        f"/api/operator/rounds/{reset['archive_id']}/archive",
        headers=OPERATOR,
    )
    assert exported.status_code == 200
    artifact = exported.json()
    snapshot = artifact["snapshot"]
    assert snapshot_hash(snapshot) == artifact["content_hash"]
    assert snapshot["round_id"] == before["round_id"]
    assert snapshot["application"]["attempts"][0]["id"] == queued["id"]
    assert snapshot["application"]["product_events"]
    assert snapshot["environments"]["protected"]["refunds"]
    assert snapshot["audit"]
    assert (
        manual_client.get("/api/operator/rounds", headers=OPERATOR).json()[0]["status"]
        == "completed"
    )
    assert (
        manual_client.get(
            f"/api/operator/rounds/{reset['archive_id']}/archive",
            headers=headers,
        ).status_code
        == 401
    )

    async def clean() -> None:
        async with core.environments.get("protected").database.sessions() as db:
            assert await db.scalar(select(func.count()).select_from(StoreRefund)) == 0
        history = await core.events.public_after(0)
        assert [event.type for event in history] == [EventType.ROUND_STARTED]
        assert history[0].data == {"round_id": reset["round_id"]}
        assert core.fleet.audit.verify().ok

    manual_client.portal.call(clean)
    next_session = join(manual_client)
    assert next_session["id"] != session["id"]
    assert next_session["token"] != session["token"]


def test_reset_rejects_in_flight_attempt_without_changing_round(manual_client: TestClient) -> None:
    session = join(manual_client)
    core: ProductCore = cast(FastAPI, manual_client.app).state.core
    assert manual_client.portal is not None
    manual_client.portal.call(core.fleet.worker.stop)
    send(manual_client, session, "Consulta A-1001.")
    before = manual_client.get("/api/arena/state").json()
    response = manual_client.post("/api/operator/reset", headers=OPERATOR, json={"reason": "nuevo"})
    assert response.status_code == 409
    after = manual_client.get("/api/arena/state").json()
    assert after["round_id"] == before["round_id"]
    assert after["accepting"] == before["accepting"]
    assert manual_client.get("/api/operator/rounds", headers=OPERATOR).json() == []


def test_startup_recovers_reset_interrupted_between_environment_and_application_commit(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configured = settings.model_copy(
        update={"runtime_poll_seconds": 0.005, "arena_auto_patch": False}
    )
    playback = {role: ScenarioPlayback() for role in ModelRole}
    with TestClient(create_app(configured, playback)) as client:
        session = join(client)
        old_round = client.get("/api/arena/state").json()["round_id"]
        core: ProductCore = cast(FastAPI, client.app).state.core
        assert client.portal is not None
        client.portal.call(stop_and_drain, core)
        original_reset = core.environments.reset

        async def interrupted() -> None:
            await original_reset()
            raise OSError("power failure after store reset")

        async def leave_reset_in_progress() -> None:
            with monkeypatch.context() as patch:
                patch.setattr(core.environments, "reset", interrupted)
                with pytest.raises(OSError, match="power failure"):
                    await core.rounds.reset("Prueba de recuperación")
            async with core.fleet.database.sessions() as db:
                archive = await db.scalar(select(RoundArchive))
                assert archive is not None
                assert archive.status == "resetting"
                assert await db.get(Attempt, "does-not-exist") is None

        client.portal.call(leave_reset_in_progress)
        assert client.get("/api/arena/state").json()["accepting"] is False
    with TestClient(
        create_app(configured, {role: ScenarioPlayback() for role in ModelRole})
    ) as client:
        after = client.get("/api/arena/state").json()
        assert after["round_id"] != old_round
        assert after["accepting"] is True
        assert after["resetting"] is False
        archives = client.get("/api/operator/rounds", headers=OPERATOR).json()
        assert len(archives) == 1
        assert archives[0]["status"] == "completed"
        assert (
            client.get(
                "/api/sessions/me", headers={"Authorization": f"Bearer {session['token']}"}
            ).status_code
            == 401
        )


def test_more_than_three_participants_receive_unique_provisioned_customers(
    settings: Settings,
) -> None:
    configured = settings.model_copy(update={"arena_session_limit": 12})
    with TestClient(
        create_app(configured, {role: ScenarioPlayback() for role in ModelRole})
    ) as client:
        sessions = [join(client, f"participante-{index}") for index in range(12)]
        assert len({session["customer_name"] for session in sessions}) == 12
        order_ids = [order for session in sessions for order in session["order_ids"]]
        assert len(order_ids) == len(set(order_ids))
        assert len(order_ids) >= 24
        assert (
            client.post(
                "/api/sessions", json={"alias": "fuera-de-cupo", "accepted_rules": True}
            ).status_code
            == 409
        )
        core: ProductCore = cast(FastAPI, client.app).state.core
        assert client.portal is not None

        async def orders() -> None:
            protected = await core.environments.get("protected").orders()
            decoy = await core.environments.get("honeypot").orders()
            assert {order["order_id"] for order in protected} == set(order_ids)
            assert {order["order_id"] for order in decoy} == set(order_ids)
            assert {order["canary"] for order in protected}.isdisjoint(
                order["canary"] for order in decoy
            )

        client.portal.call(orders)


async def test_concurrent_session_allocators_obey_round_capacity(settings: Settings) -> None:
    database = Database(settings.app_database_url)
    await database.create_schema()

    async def allocate(index: int) -> ArenaSession | None:
        async with database.sessions() as db:
            try:
                return await create_session(
                    db, SessionCreate(alias=f"player-{index}", accepted_rules=True), 7
                )
            except ValueError:
                return None

    try:
        results = await asyncio.gather(*(allocate(index) for index in range(20)))
        created = [session for session in results if session is not None]
        assert len(created) == 7
        assert len({session.customer_id for session in created}) == 7
    finally:
        await database.dispose()
