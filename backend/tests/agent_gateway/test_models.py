from agent_zero.agent_gateway.models import GatewayDecision, GatewayReason, GatewayStage


def test_decisions_match_the_catalog() -> None:
    assert {d.value for d in GatewayDecision} == {"allow", "deny", "redact"}


def test_stages_are_declared_in_pipeline_order() -> None:
    assert [s.value for s in GatewayStage] == [
        "identity",
        "policy",
        "input_armor",
        "tool",
        "output_armor",
        "audit",
    ]


def test_reasons_are_unique_snake_case() -> None:
    values = [reason.value for reason in GatewayReason]
    assert len(values) == len(set(values))
    assert all(value == value.lower() and " " not in value for value in values)
