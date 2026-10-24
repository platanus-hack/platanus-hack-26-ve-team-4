import asyncio
from typing import cast
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.arena.core import ProductCore
from agent_zero.attempts.models import Attempt
from agent_zero.attempts.schemas import AttemptCreate
from agent_zero.events.broker import EventBroker
from agent_zero.events.event_store import EventStore
from agent_zero.events.models import EventDelivery, EventRecord, EventType
from agent_zero.events.schemas import EventDraft
from agent_zero.events.sse import public_stream
from agent_zero.runtime.models import Run
from tests.arena.support import join


def test_queue_and_outbox_roll_back_together_on_commit_failure(
    manual_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = join(manual_client)
    core: ProductCore = cast(FastAPI, manual_client.app).state.core

    async def fail_at_commit() -> None:
        await core.worker.stop()
        await core.fleet.worker.stop()
        with monkeypatch.context() as patch:
            patch.setattr(
                AsyncSession, "commit", AsyncMock(side_effect=OSError("disk unavailable"))
            )
            with pytest.raises(OSError, match="disk unavailable"):
                await core.submissions.submit(
                    session["id"],
                    AttemptCreate(
                        message="Consulta A-1001.",
                        idempotency_key="atomic-queue",
                    ),
                )
        async with core.fleet.database.sessions() as db:
            assert await db.scalar(select(func.count()).select_from(Attempt)) == 0
            assert await db.scalar(select(func.count()).select_from(Run)) == 0
            assert await db.scalar(select(func.count()).select_from(EventRecord)) == 0
            assert await db.scalar(select(func.count()).select_from(EventDelivery)) == 0

    assert manual_client.portal is not None
    manual_client.portal.call(fail_at_commit)


def test_accepted_queue_recovers_after_crash_before_any_publication(
    manual_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = join(manual_client)
    core: ProductCore = cast(FastAPI, manual_client.app).state.core

    async def recover() -> None:
        await core.worker.stop()
        await core.fleet.worker.stop()
        payload = AttemptCreate(message="Consulta A-1001.", idempotency_key="lost-response")
        with monkeypatch.context() as patch:
            patch.setattr(core.events, "dispatch_pending", AsyncMock(side_effect=OSError("crash")))
            with pytest.raises(OSError, match="crash"):
                await core.submissions.submit(session["id"], payload)
        # A client retries the request whose response was lost. No new run is created.
        duplicate = await core.submissions.submit(session["id"], payload)
        broker = EventBroker()
        recovered = EventStore(core.fleet, broker)
        await recovered.restore()
        async with core.fleet.database.sessions() as db:
            assert await db.scalar(select(func.count()).select_from(Attempt)) == 1
            assert await db.scalar(select(func.count()).select_from(Run)) == 1
            assert await db.scalar(select(func.count()).select_from(EventRecord)) == 2
            undelivered = await db.scalar(
                select(func.count())
                .select_from(EventDelivery)
                .where(EventDelivery.delivered_at.is_(None))
            )
            assert undelivered == 0
        events = await recovered.for_attempt(duplicate.id)
        assert [event.type for event in events] == [EventType.ATTEMPT_QUEUED]
        public = await recovered.public_after(0)
        assert len(public) == 1
        assert public[0].data == {"status": "queued"}
        assert core.fleet.audit.verify().ok

    assert manual_client.portal is not None
    manual_client.portal.call(recover)


def test_recovery_after_audit_append_avoids_duplicate_audit_entries_and_sse(
    manual_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core: ProductCore = cast(FastAPI, manual_client.app).state.core

    async def recover() -> None:
        await core.worker.stop()
        broker = EventBroker()
        events = EventStore(core.fleet, broker)
        with monkeypatch.context() as patch:

            def fail_publish(event: object) -> None:
                raise OSError("transport crash")

            patch.setattr(broker, "publish_event", fail_publish)
            with pytest.raises(OSError, match="transport crash"):
                await events.public(
                    EventType.ATTEMPT_QUEUED, 0, status="queued", dedup_key="transport"
                )
        before = [entry for entry in core.fleet.audit.entries() if entry.actor == "arena"]
        assert len(before) == 1
        async with broker.subscribe() as queue:
            assert await events.dispatch_pending() == 1
            assert await events.dispatch_pending() == 0
            assert queue.qsize() == 1
            event_id = queue.get_nowait().id
        after = [entry for entry in core.fleet.audit.entries() if entry.actor == "arena"]
        assert len(after) == 1
        assert after[0].attributes["event_id"] == event_id
        assert core.fleet.audit.verify().ok

    assert manual_client.portal is not None
    manual_client.portal.call(recover)


def test_two_event_stores_racing_on_same_key_persist_and_audit_once(
    manual_client: TestClient,
) -> None:
    core: ProductCore = cast(FastAPI, manual_client.app).state.core

    async def race() -> None:
        await core.worker.stop()
        stores = [EventStore(core.fleet, EventBroker()) for _ in range(8)]
        results = await asyncio.gather(
            *(
                store.emit(
                    EventDraft(type=EventType.ATTEMPT_STARTED, attempt_id="attempt-concurrent"),
                    dedup_key="same-event",
                )
                for store in stores
            )
        )
        assert len({event.id for event in results}) == 1
        async with core.fleet.database.sessions() as db:
            assert await db.scalar(select(func.count()).select_from(EventRecord)) == 1
        audited = [entry for entry in core.fleet.audit.entries() if entry.actor == "arena"]
        assert len(audited) == 1
        assert core.fleet.audit.verify().ok

    assert manual_client.portal is not None
    manual_client.portal.call(race)


def test_sse_reads_remote_process_events_in_order_without_local_broker_notifications(
    manual_client: TestClient,
) -> None:
    core: ProductCore = cast(FastAPI, manual_client.app).state.core

    async def remote() -> None:
        await core.worker.stop()
        local_broker, remote_broker = EventBroker(), EventBroker()
        local_events = EventStore(core.fleet, local_broker)
        remote_events = EventStore(core.fleet, remote_broker)
        await local_events.restore()
        await remote_events.restore()
        stream = public_stream(local_broker, after_id=0, heartbeat_seconds=0.01)
        await remote_events.public(EventType.ATTEMPT_QUEUED, 0, status="remote-first")
        first = await asyncio.wait_for(anext(stream), 2)
        assert "remote-first" in first
        await remote_events.public(EventType.ATTEMPT_QUEUED, 0, status="remote-second")
        await local_events.public(EventType.ATTEMPT_QUEUED, 0, status="local-third")
        second = await asyncio.wait_for(anext(stream), 2)
        third = await asyncio.wait_for(anext(stream), 2)
        await stream.aclose()
        assert "remote-second" in second
        assert "local-third" in third
        ids = [int(frame.splitlines()[0].removeprefix("id: ")) for frame in (first, second, third)]
        assert ids == sorted(set(ids))

    assert manual_client.portal is not None
    manual_client.portal.call(remote)
