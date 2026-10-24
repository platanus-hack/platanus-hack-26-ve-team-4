import pytest

from agent_zero.llm.models import CallOutcome
from agent_zero.llm.reporting import summarize
from agent_zero.llm.schemas import CallCost, CallUsage
from tests.llm.records import call_record


def test_summary_groups_by_role_and_adds_usage_and_cost() -> None:
    records = [
        call_record(
            "victim", latency_ms=10, usage=CallUsage(input_tokens=10), cost=CallCost(input_usd=0.1)
        ),
        call_record("victim", CallOutcome.REFUSED, latency_ms=30, usage=CallUsage(output_tokens=5)),
        call_record("analyzer", CallOutcome.DENIED, latency_ms=0),
    ]

    analyzer, victim = summarize(records)

    assert analyzer.role == "analyzer"
    assert analyzer.outcomes[CallOutcome.DENIED] == 1
    assert victim.calls == 2
    assert victim.usage == CallUsage(input_tokens=10, output_tokens=5)
    assert victim.cost.total_usd == pytest.approx(0.1)
    assert victim.unpriced_calls == 1
    assert victim.mean_latency_ms == pytest.approx(20)
    assert victim.measured_calls == 0


def test_empty_ledger_has_empty_summary() -> None:
    assert summarize([]) == []
