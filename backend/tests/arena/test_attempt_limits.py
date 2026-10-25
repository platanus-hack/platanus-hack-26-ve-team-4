from collections.abc import Iterator, Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_zero.arena.core import ProductCore
from agent_zero.attempts.attempt_submission_service import (
    QUEUE_RETRY_SECONDS,
    AttemptSubmissionService,
)
from agent_zero.config import Settings
from agent_zero.llm.models import ModelRole
from agent_zero.main import create_app
from tests.arena.support import OPERATOR, ScenarioPlayback, join

pytestmark = pytest.mark.requirement("CORE-01")

PER_MINUTE = "Alcanzaste el límite de intentos por minuto."
QUEUE_FULL = "La cola está llena; espera el resultado anterior."


class Reply(Protocol):
    """The part of the test client's response these tests read."""

    @property
    def status_code(self) -> int: ...
    @property
    def headers(self) -> Mapping[str, str]: ...
    @property
    def text(self) -> str: ...
    def json(self) -> Any: ...


class StepClock:
    """A clock the test moves by hand; admission never reads the real time."""

    def __init__(self, start: datetime) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now


def client_with(settings: Settings, **update: Any) -> TestClient:
    configured = settings.model_copy(
        update={
            "runtime_poll_seconds": 0.005,
            "arena_session_limit": 3,
            "gateway_rate_limit_per_minute": 10000,
            "arena_auto_patch": False,
        }
        | update
    )
    return TestClient(create_app(configured, {role: ScenarioPlayback() for role in ModelRole}))


def core_of(client: TestClient) -> ProductCore:
    core: ProductCore = cast(FastAPI, client.app).state.core
    return core


def hold_queue(client: TestClient) -> None:
    """Stop the run worker so every accepted attempt stays queued (in flight)."""
    assert client.portal is not None
    client.portal.call(core_of(client).fleet.worker.stop)


def post(client: TestClient, session: dict[str, Any], key: str, **body: Any) -> Reply:
    return client.post(
        "/api/attempts",
        headers={"Authorization": f"Bearer {session['token']}"},
        json={"message": "¿Cuánto tarda el envío?", "idempotency_key": key} | body,
    )


def attempt_count(client: TestClient) -> int:
    return len(client.get("/api/operator/attempts", headers=OPERATOR).json())


@pytest.fixture
def queued_client(settings: Settings) -> Iterator[TestClient]:
    with client_with(settings) as client:
        hold_queue(client)
        yield client


def test_a_message_of_4000_characters_is_accepted_and_one_of_4001_is_rejected(
    queued_client: TestClient,
) -> None:
    first, second = join(queued_client, "neo"), join(queued_client, "trinity")
    too_long = "a" * 4001
    rejected = [
        post(queued_client, first, "long-single", message=too_long),
        post(queued_client, first, "long-list", message=None, messages=["Hola", too_long]),
    ]
    assert [response.status_code for response in rejected] == [422, 422]
    assert attempt_count(queued_client) == 0
    longest = "a" * 4000
    single = post(queued_client, first, "edge-single", message=longest)
    listed = post(queued_client, second, "edge-list", message=None, messages=["Hola", longest])
    assert single.status_code == 202, single.text
    assert listed.status_code == 202, listed.text
    assert single.json()["messages"] == [longest]
    assert attempt_count(queued_client) == 2


def test_a_second_pending_attempt_of_the_same_session_gets_429_with_retry_after(
    queued_client: TestClient,
) -> None:
    session = join(queued_client)
    assert post(queued_client, session, "pending").status_code == 202
    response = post(queued_client, session, "while-pending")
    assert response.status_code == 429
    assert response.json()["detail"] == QUEUE_FULL
    assert response.headers["Retry-After"] == str(QUEUE_RETRY_SECONDS) == "5"
    assert attempt_count(queued_client) == 1
    # Another session is not affected by this session's pending attempt.
    assert post(queued_client, join(queued_client, "trinity"), "other").status_code == 202


def test_a_full_round_queue_gets_429_with_retry_after(settings: Settings) -> None:
    with client_with(settings, arena_queue_limit=1) as client:
        hold_queue(client)
        assert post(client, join(client, "neo"), "first").status_code == 202
        response = post(client, join(client, "trinity"), "second")
        assert response.status_code == 429
        assert response.json()["detail"] == QUEUE_FULL
        assert response.headers["Retry-After"] == "5"
        assert attempt_count(client) == 1


def test_the_per_minute_limit_slides_and_reports_when_the_oldest_attempt_leaves(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The test fixes 12 so its clock marks (4 s apart in a 60 s window) keep their
    # meaning; the default of 240 is checked by its own test. Only the pending-per-session
    # limit is lifted so queued attempts do not mask the per-minute limit.
    with client_with(
        settings, arena_session_queue_limit=50, arena_attempts_per_minute=12
    ) as client:
        assert core_of(client).fleet.settings.arena_attempts_per_minute == 12
        hold_queue(client)
        core = core_of(client)
        start = datetime.now(UTC).replace(microsecond=0)
        clock = StepClock(start)
        monkeypatch.setattr(
            core,
            "submissions",
            AttemptSubmissionService(
                replace(core.fleet, clock=clock),
                core.policies,
                core.events,
                core.routing,
                core.admission_lock,
            ),
        )
        session = join(client)
        for index in range(12):
            clock.now = start + timedelta(seconds=4 * index)
            accepted = post(client, session, f"inside-{index}")
            assert accepted.status_code == 202, accepted.text

        def limited(at: timedelta) -> str:
            clock.now = start + at
            response = post(client, session, f"limited-{at.total_seconds()}")
            assert response.status_code == 429, response.text
            assert response.json()["detail"] == PER_MINUTE
            return response.headers["Retry-After"]

        # The attempt from `start` leaves the window 60 s later.
        assert limited(timedelta(seconds=50)) == "10"
        assert limited(timedelta(seconds=59, milliseconds=500)) == "1"
        assert limited(timedelta(seconds=60)) == "1"
        assert attempt_count(client) == 12

        clock.now = start + timedelta(seconds=60, milliseconds=1)
        assert post(client, session, "after-window").status_code == 202
        # Full again: the next to leave is the attempt from `start + 4 s`.
        assert limited(timedelta(seconds=60, milliseconds=1)) == "4"
        assert attempt_count(client) == 13


def test_the_default_per_minute_limit_is_240_and_reaches_the_participant(
    settings: Settings,
) -> None:
    assert Settings.model_fields["arena_attempts_per_minute"].default == 240
    with client_with(settings) as client:
        assert join(client)["limits"]["attempts_per_minute"] == 240
