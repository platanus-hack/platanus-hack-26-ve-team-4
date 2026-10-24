import pytest
from fastapi.testclient import TestClient


@pytest.mark.requirement("REG-03")
def test_operator_routes_need_the_secret(api: TestClient) -> None:
    assert api.post("/api/registry/agents", json={}).status_code == 401
    wrong = {"X-Operator-Secret": "otro"}
    assert (
        api.post("/api/registry/agents/a/versions/1.0.0/approve", headers=wrong).status_code == 401
    )
    assert (
        api.post("/api/registry/agents/a/versions/1.0.0/deprecate", headers=wrong).status_code
        == 401
    )


def test_public_reads_do_not_need_the_secret(api: TestClient) -> None:
    assert api.get("/api/registry/agents").status_code == 200
