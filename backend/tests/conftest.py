from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent_zero.config import Settings
from agent_zero.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path, environment="test")


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client
