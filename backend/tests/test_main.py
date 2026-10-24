from fastapi.testclient import TestClient

from agent_zero.llm.gateway import LlmGateway
from agent_zero.llm.models import LlmMode


def test_app_starts_with_an_offline_llm_gateway(client: TestClient) -> None:
    gateway = client.app.state.llm  # type: ignore[attr-defined]

    assert isinstance(gateway, LlmGateway)
    assert gateway.mode is LlmMode.OFFLINE
