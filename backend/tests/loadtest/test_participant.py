import asyncio
import json

import httpx
import pytest

from agent_zero.loadtest import participant
from agent_zero.loadtest.participant import AttemptRecord, Pace, run_participant


def fake_arena(throttle_first: bool) -> httpx.MockTransport:
    calls = {"submit": 0}

    def answer(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/sessions":
            return httpx.Response(201, json={"token": "t", "order_ids": ["A-1001"]})
        if request.method == "POST":
            calls["submit"] += 1
            if throttle_first and calls["submit"] == 1:
                return httpx.Response(429, headers={"Retry-After": "0"})
            body = json.loads(request.content)
            assert body["idempotency_key"].startswith("stress-")
            return httpx.Response(202, json={"id": f"attempt-{calls['submit']}"})
        return httpx.Response(200, json={"status": "evaluated", "outcome": "not_achieved"})

    return httpx.MockTransport(answer)


def run(transport: httpx.MockTransport, attempts: int) -> list[AttemptRecord]:
    async def go() -> list[AttemptRecord]:
        async with httpx.AsyncClient(transport=transport, base_url="http://arena") as client:
            return await run_participant(client, "p", Pace(attempts, 0.0), 1)

    return asyncio.run(go())


def test_participant_retries_throttled_submissions_and_waits_for_the_result() -> None:
    records = run(fake_arena(throttle_first=True), 2)
    assert len(records) == 2
    assert records[0].throttled == 1
    assert all(record.status == "evaluated" for record in records)
    assert all(record.latency is not None for record in records)


def test_join_failures_are_recorded_without_raising() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(409))
    records = run(transport, 2)
    assert [record.errors for record in records] == [["join 409"]]


def test_unfinished_attempts_time_out(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(participant, "ATTEMPT_TIMEOUT", 0.0)
    records = run(fake_arena(throttle_first=False), 1)
    assert records[0].status == "timeout"


def test_deadline_stops_the_participant_and_honest_persona_never_attacks() -> None:
    async def go() -> list[AttemptRecord]:
        transport = fake_arena(throttle_first=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://arena") as client:
            return await run_participant(client, "p", Pace(50, 0.0, 0.0), 1, "honest")

    assert asyncio.run(go()) == []


def test_honest_persona_is_recorded_as_honest() -> None:
    async def go() -> list[AttemptRecord]:
        transport = fake_arena(throttle_first=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://arena") as client:
            return await run_participant(client, "p", Pace(3, 0.0), 7, "honest")

    assert {record.kind for record in asyncio.run(go())} == {"honest"}
