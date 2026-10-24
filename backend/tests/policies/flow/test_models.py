from agent_zero.policies.flow.models import FlowPolicyRecord


def test_flow_rules_live_in_their_own_table_keyed_by_version() -> None:
    assert FlowPolicyRecord.__tablename__ == "policy_flow_rules"
    assert [column.name for column in FlowPolicyRecord.__table__.primary_key] == ["version"]
