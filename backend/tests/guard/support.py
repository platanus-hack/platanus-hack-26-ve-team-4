from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from agent_zero.config import Settings
from agent_zero.contract.schema import LegitimateCall
from agent_zero.main import create_app
from tests.contract.support import CONTRACTS_DIR

GUARD = {"X-Guard-Key": "change-me-guard"}
OPERATOR = {"X-Operator-Secret": "change-me"}
SUBJECT = "ana"


@contextmanager
def guard_client(settings: Settings, contracts: Path = CONTRACTS_DIR) -> Iterator[TestClient]:
    with TestClient(create_app(settings.model_copy(update={"contracts_dir": contracts}))) as client:
        yield client


def resolve(owners: dict[str, str]) -> dict[str, str]:
    return {name: SUBJECT if owner == "subject" else owner for name, owner in owners.items()}


def legitimate_request(call: LegitimateCall) -> dict[str, Any]:
    return {
        "subject": SUBJECT,
        "tool": call.tool,
        "arguments": call.arguments,
        "provenance": call.provenance,
        "owners": resolve(call.owners),
    }


def check(client: TestClient, contract_id: str, body: dict[str, Any]) -> dict[str, Any]:
    response = client.post(f"/api/guard/{contract_id}/check", json=body, headers=GUARD)
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


def effects(client: TestClient, contract_id: str, call_id: str, **extra: Any) -> dict[str, Any]:
    body = {"call_id": call_id, **extra}
    response = client.post(f"/api/guard/{contract_id}/effects", json=body, headers=GUARD)
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result
