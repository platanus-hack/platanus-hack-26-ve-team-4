from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from agent_zero.config import Settings
from agent_zero.llm.models import ModelRole
from agent_zero.main import create_app
from tests.decoy.support import DecoyPlayback


@pytest.fixture
def playbacks() -> dict[ModelRole, DecoyPlayback]:
    return {role: DecoyPlayback() for role in ModelRole}


@pytest.fixture
def decoy_client(
    settings: Settings, playbacks: dict[ModelRole, DecoyPlayback]
) -> Iterator[TestClient]:
    configured = settings.model_copy(
        update={
            "runtime_poll_seconds": 0.005,
            "arena_session_limit": 3,
            "gateway_rate_limit_per_minute": 10000,
            "arena_auto_patch": False,
        }
    )
    with TestClient(create_app(configured, dict(playbacks))) as client:
        yield client
