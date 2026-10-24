from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from agent_zero.config import Settings
from agent_zero.llm.models import ModelRole
from agent_zero.main import create_app
from tests.arena.support import ScenarioPlayback


@pytest.fixture
def live_client(settings: Settings) -> Iterator[TestClient]:
    configured = settings.model_copy(
        update={
            "runtime_poll_seconds": 0.005,
            "arena_session_limit": 6,
            "gateway_rate_limit_per_minute": 10000,
            "arena_auto_patch": False,
        }
    )
    with TestClient(
        create_app(configured, {role: ScenarioPlayback() for role in ModelRole})
    ) as client:
        yield client
