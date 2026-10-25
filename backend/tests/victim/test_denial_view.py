import pytest

from agent_zero.agent_gateway.errors import GatewayDeniedError
from agent_zero.agent_gateway.models import GatewayReason, GatewayStage
from agent_zero.victim.denial_view import ORDER_DENIAL_GUIDANCE, denial_output

pytestmark = pytest.mark.requirement("CORE-06")

BUSINESS = GatewayDeniedError(GatewayReason.BUSINESS_RULE_DENIED, GatewayStage.POLICY)


@pytest.mark.parametrize("tool", ["get_order", "request_refund"])
def test_order_denials_guide_without_revealing_the_cause(tool: str) -> None:
    output = denial_output(tool, BUSINESS)
    assert output == {"denied": "business_rule_denied", "guidance": ORDER_DENIAL_GUIDANCE}
    assert "no existe" not in ORDER_DENIAL_GUIDANCE.lower()
    assert "otro cliente" not in ORDER_DENIAL_GUIDANCE.lower()


def test_other_denials_keep_only_the_reason() -> None:
    assert denial_output("save_memory", BUSINESS) == {"denied": "business_rule_denied"}
