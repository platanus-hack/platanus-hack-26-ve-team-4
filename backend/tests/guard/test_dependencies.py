from pathlib import Path

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from pydantic import SecretStr

from agent_zero.config import Settings
from agent_zero.main import create_app
from tests.contract.support import CONTRACTS_DIR

BODY = {"subject": "ana", "tool": "get_order", "arguments": {"order_id": "A"}}


def production(tmp_path: Path, guard_key: str) -> Settings:
    return Settings(
        data_dir=tmp_path,
        environment="production",
        identity_signing_key=SecretStr("i" * 40),
        operator_secret=SecretStr("o" * 40),
        memory_encryption_key=SecretStr(Fernet.generate_key().decode()),
        guard_api_key=SecretStr(guard_key),
        contracts_dir=CONTRACTS_DIR,
    )


def test_a_weak_guard_key_disables_the_guard_but_not_the_app(tmp_path: Path) -> None:
    with TestClient(create_app(production(tmp_path, "change-me-guard"))) as client:
        assert client.get("/health").status_code == 200
        headers = {"X-Guard-Key": "change-me-guard"}
        response = client.post("/api/guard/yummy-soporte/check", json=BODY, headers=headers)
        assert response.status_code == 503


def test_a_strong_guard_key_is_required_and_accepted(tmp_path: Path) -> None:
    key = "g" * 40
    with TestClient(create_app(production(tmp_path, key))) as client:
        url = "/api/guard/yummy-soporte/check"
        assert client.post(url, json=BODY, headers={"X-Guard-Key": "otra"}).status_code == 401
        assert client.post(url, json=BODY, headers={"X-Guard-Key": key}).status_code == 200
