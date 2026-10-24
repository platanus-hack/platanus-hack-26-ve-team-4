from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from agent_zero.config import Settings
from agent_zero.fleet.startup_guard import InsecureConfigurationError, enforce_secure_settings
from agent_zero.main import create_app

STRONG_A = "a" * 40
STRONG_B = "b" * 40
STRONG_C = "c" * 40


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "data_dir": tmp_path,
        "environment": "production",
        "identity_signing_key": STRONG_A,
        "operator_secret": STRONG_B,
        "session_signing_key": STRONG_C,
        "memory_encryption_key": Fernet.generate_key().decode(),
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


@pytest.mark.requirement("IDN-01", "IDN-02")
@pytest.mark.parametrize(
    "overrides",
    [
        {"identity_signing_key": "change-me-identity"},
        {"operator_secret": "change-me"},
        {"identity_signing_key": "corta"},
        {"operator_secret": "corta"},
        {"identity_signing_key": STRONG_B},
        {"session_signing_key": "change-me-session"},
        {"session_signing_key": "corta"},
        {"session_signing_key": STRONG_A},
        {"session_signing_key": STRONG_B},
    ],
)
def test_production_refuses_default_short_or_shared_secrets(
    tmp_path: Path, overrides: dict[str, object]
) -> None:
    with pytest.raises(InsecureConfigurationError):
        enforce_secure_settings(_settings(tmp_path, **overrides))


@pytest.mark.requirement("IDN-01", "IDN-02")
def test_error_lists_every_problem(tmp_path: Path) -> None:
    settings = _settings(tmp_path, identity_signing_key="change-me-identity", operator_secret="x")
    with pytest.raises(InsecureConfigurationError) as caught:
        enforce_secure_settings(settings)
    assert len(caught.value.problems) == 2
    assert "AGENT_ZERO_IDENTITY_SIGNING_KEY" in str(caught.value)


@pytest.mark.requirement("IDN-01", "IDN-02")
def test_strong_secrets_pass_in_production(tmp_path: Path) -> None:
    enforce_secure_settings(_settings(tmp_path))


@pytest.mark.requirement("IDN-01", "IDN-02")
@pytest.mark.parametrize("environment", ["local", "test"])
def test_local_and_test_keep_the_defaults(tmp_path: Path, environment: str) -> None:
    enforce_secure_settings(Settings(data_dir=tmp_path, environment=environment))


@pytest.mark.requirement("IDN-01", "IDN-02")
def test_app_refuses_to_start_with_default_secrets_in_production(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, environment="production")
    with pytest.raises(InsecureConfigurationError), TestClient(create_app(settings)):
        pass


@pytest.mark.requirement("IDN-01", "IDN-02")
def test_app_starts_in_production_with_strong_secrets(tmp_path: Path) -> None:
    with TestClient(create_app(_settings(tmp_path))) as client:
        assert client.get("/health").status_code == 200
