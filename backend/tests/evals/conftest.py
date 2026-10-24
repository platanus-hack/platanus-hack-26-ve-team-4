from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from agent_zero.config import Settings
from agent_zero.llm.models import LlmMode
from agent_zero.main import create_app


@pytest.fixture
def evaluation_settings(settings: Settings) -> Settings:
    return settings.model_copy(
        update={
            "llm_mode": LlmMode.DEMO,
            "arena_auto_patch": False,
            "runtime_poll_seconds": 0.002,
            "gateway_rate_limit_per_minute": 100000,
            "llm_daily_call_limit": 10000,
            "llm_campaign_call_limit": 1200,
        }
    )


@pytest.fixture
def evaluation_client(evaluation_settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(evaluation_settings)) as client:
        yield client
