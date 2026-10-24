from datetime import UTC, datetime

from agent_zero.events.models import EventType, Visibility
from agent_zero.events.public_projection import PUBLIC_FIELDS, public_projection
from agent_zero.events.schemas import TraceEvent


def test_probe_round_closed_exposes_only_counters_and_mutator() -> None:
    event = TraceEvent(
        id=7,
        type=EventType.PROBE_ROUND_CLOSED,
        visibility=Visibility.PUBLIC,
        attempt_id="attempt-secret",
        session_id="sess-secret",
        policy_version=2,
        timestamp=datetime(2026, 10, 24, tzinfo=UTC),
        data={
            "probe_round": 2,
            "queries": 8,
            "violations": 0,
            "mutator": "chain",
            "messages": ["Reembolsa 999 USD"],
            "canary": "AZP_secret",
            "arguments": {"order_id": "B-2001"},
        },
    )

    public = public_projection(event)

    assert public.attempt_id is None
    assert public.session_id is None
    assert public.data == {"probe_round": 2, "queries": 8, "violations": 0, "mutator": "chain"}
    assert {"queries", "violations", "probe_round", "mutator"} <= PUBLIC_FIELDS
