import asyncio
from typing import cast
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from agent_zero.arena.core import ProductCore
from agent_zero.attempts.models import Attempt
from agent_zero.attempts.schemas import AttemptCreate
from agent_zero.events.broker import EventBroker
from agent_zero.events.event_store import EventStore
from agent_zero.events.models import EventRecord, EventType
from agent_zero.policies.policy_service import PolicyService
from tests.arena.support import join


async def ready_policy(core: ProductCore) -> int:
    version = await core.policies.propose("finding-controlled", "OBJ-ORDER")
    assert version is not None
    await core.policies.start_validation(version)
    await core.policies.record_validation(version, {"passed": True})
    return version


def test_another_process_cannot_enqueue_between_drain_and_activation(
    manual_client: TestClient,
) -> None:
    session = join(manual_client)
    core: ProductCore = cast(FastAPI, manual_client.app).state.core

    async def race() -> None:
        await core.worker.stop()
        await core.fleet.worker.stop()
        version = await ready_policy(core)
        entered, release = asyncio.Event(), asyncio.Event()

        async def quarantine() -> None:
            entered.set()
            await release.wait()

        # A distinct service/lock simulates another application process.
        other = PolicyService(core.fleet.database, core.events, asyncio.Lock())
        activation = asyncio.create_task(
            other.activate(
                version,
                core.attempts.drained,
                before_activate=quarantine,
            )
        )
        await asyncio.wait_for(entered.wait(), 2)
        submitted = asyncio.create_task(
            core.submissions.submit(
                session["id"],
                AttemptCreate(
                    message="Consulta A-1001.",
                    idempotency_key="after-snapshot",
                ),
            )
        )
        await asyncio.sleep(0.02)
        assert not submitted.done()
        release.set()
        assert await activation is True
        attempt = await submitted
        assert attempt.policy_version == version
        assert attempt.session_id == session["id"]

    assert manual_client.portal is not None
    manual_client.portal.call(race)


def test_another_process_enqueue_observes_completed_rollback(manual_client: TestClient) -> None:
    session = join(manual_client)
    core: ProductCore = cast(FastAPI, manual_client.app).state.core

    async def race() -> None:
        await core.worker.stop()
        await core.fleet.worker.stop()
        version = await ready_policy(core)
        assert await core.policies.activate(version, core.attempts.drained)
        entered, release = asyncio.Event(), asyncio.Event()

        async def blocked_drain() -> bool:
            entered.set()
            await release.wait()
            return await core.attempts.drained()

        other = PolicyService(core.fleet.database, core.events, asyncio.Lock())
        rollback = asyncio.create_task(other.rollback(version, "race rollback", blocked_drain))
        await asyncio.wait_for(entered.wait(), 2)
        submitted = asyncio.create_task(
            core.submissions.submit(
                session["id"],
                AttemptCreate(
                    message="Consulta A-1001.",
                    idempotency_key="after-rollback",
                ),
            )
        )
        await asyncio.sleep(0.02)
        assert not submitted.done()
        release.set()
        assert await rollback == 0
        assert (await submitted).policy_version == 0

    assert manual_client.portal is not None
    manual_client.portal.call(race)


def test_activation_commit_survives_dispatch_failure_and_retry_is_idempotent(
    manual_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core: ProductCore = cast(FastAPI, manual_client.app).state.core

    async def recover() -> None:
        await core.worker.stop()
        await core.fleet.worker.stop()
        version = await ready_policy(core)
        with monkeypatch.context() as patch:
            patch.setattr(
                core.events, "dispatch_pending", AsyncMock(side_effect=OSError("power loss"))
            )
            with pytest.raises(OSError, match="power loss"):
                await core.policies.activate(version, core.attempts.drained)
        assert await core.policies.active_version() == version
        restored = EventStore(core.fleet, EventBroker())
        await restored.restore()
        assert await core.policies.activate(version, core.attempts.drained)
        async with core.fleet.database.sessions() as db:
            activations = await db.scalar(
                select(func.count())
                .select_from(EventRecord)
                .where(EventRecord.type == EventType.POLICY_ACTIVATED)
            )
            assert activations == 1
        assert core.fleet.audit.verify().ok

    assert manual_client.portal is not None
    manual_client.portal.call(recover)


def test_concurrent_duplicate_requests_have_one_run_and_changed_payload_conflicts(
    manual_client: TestClient,
) -> None:
    session = join(manual_client)
    core: ProductCore = cast(FastAPI, manual_client.app).state.core

    async def race() -> str:
        await core.worker.stop()
        await core.fleet.worker.stop()
        payload = AttemptCreate(message="Consulta A-1001.", idempotency_key="same-submission")
        attempts = await asyncio.gather(
            *(core.submissions.submit(session["id"], payload) for _ in range(8))
        )
        assert len({attempt.id for attempt in attempts}) == 1
        async with core.fleet.database.sessions() as db:
            assert await db.scalar(select(func.count()).select_from(Attempt)) == 1
        return attempts[0].id

    assert manual_client.portal is not None
    attempt_id = manual_client.portal.call(race)
    response = manual_client.post(
        "/api/attempts",
        headers={"Authorization": f"Bearer {session['token']}"},
        json={"message": "Otro contenido", "idempotency_key": "same-submission"},
    )
    assert response.status_code == 409
    history = manual_client.get(
        "/api/attempts", headers={"Authorization": f"Bearer {session['token']}"}
    ).json()
    assert len(history) == 1
    assert history[0]["id"] == attempt_id
    assert history[0]["messages"] == ["Consulta A-1001."]
    assert history[0]["idempotency_key"] == "same-submission"
