from datetime import UTC, datetime

from fastapi.testclient import TestClient

from agent_zero.events.models import EventType, Visibility
from agent_zero.events.public_projection import public_projection
from agent_zero.events.schemas import TraceEvent
from tests.arena.support import join


def test_operator_summary_needs_the_operator_secret(decoy_client: TestClient) -> None:
    assert decoy_client.get("/api/operator/decoy").status_code == 401
    assert (
        decoy_client.get("/api/operator/decoy", headers={"X-Operator-Secret": "otro"}).status_code
        == 401
    )


def test_reveal_card_needs_a_session_and_stays_closed_before_the_reveal(
    decoy_client: TestClient,
) -> None:
    assert decoy_client.get("/api/decoy/reveal").status_code == 401
    session = join(decoy_client)
    response = decoy_client.get(
        "/api/decoy/reveal", headers={"Authorization": f"Bearer {session['token']}"}
    )

    assert response.status_code == 403
    assert "señuelo" not in response.text


def test_honeytool_events_reach_the_public_stream_without_tool_or_output() -> None:
    event = TraceEvent(
        id=7,
        type=EventType.TOOL_COMPLETED,
        visibility=Visibility.OPERATOR,
        attempt_id="att-1",
        session_id="sess-a",
        data={
            "tool": "get_service_credentials",
            "output": '{"clave_api": "AZH-KEY-ABCD-EFGH-JKLM"}',
            "environment": "honeypot",
            "status": "tool_completed",
        },
        timestamp=datetime(2026, 10, 24, tzinfo=UTC),
    )

    projected = public_projection(event)

    assert projected.data == {"status": "tool_completed"}
    assert projected.session_id is None
    assert "AZH" not in projected.model_dump_json()
