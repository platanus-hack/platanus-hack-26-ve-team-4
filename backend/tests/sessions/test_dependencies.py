from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from agent_zero.config import Settings
from agent_zero.llm.models import LlmMode
from agent_zero.main import create_app
from tests.arena.support import join, send
from tests.conftest import POSTGRES_URL


def test_requests_without_a_bearer_token_are_rejected(client: TestClient) -> None:
    assert client.get("/api/sessions/me").status_code == 401
    bad = client.get("/api/sessions/me", headers={"Authorization": "Bearer nada"})
    assert bad.status_code == 401


@pytest.mark.skipif(POSTGRES_URL is None, reason="El agotamiento del pool solo existe en Postgres.")
def test_authenticated_reads_do_not_hold_a_connection_while_the_handler_runs(
    settings: Settings,
) -> None:
    tight = settings.model_copy(
        update={"llm_mode": LlmMode.DEMO, "database_pool_size": 1, "database_max_overflow": 0}
    )
    with TestClient(create_app(tight)) as client:
        session = join(client, "pool-uno")
        attempt = send(client, session, "Consulta mi pedido.")
        headers = {"Authorization": f"Bearer {session['token']}"}

        def read(_: int) -> int:
            response = client.get(f"/api/attempts/{attempt['id']}", headers=headers)
            return response.status_code

        with ThreadPoolExecutor(max_workers=4) as pool:
            assert set(pool.map(read, range(8))) == {200}
