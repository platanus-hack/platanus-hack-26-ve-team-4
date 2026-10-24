import pytest
from pydantic import ValidationError

from agent_zero.agent_gateway.models import GatewayDecision, GatewayReason
from agent_zero.agent_gateway.schemas import GatewayResult, ToolSpec
from agent_zero.shared.classification import DataClassification


def test_tool_spec_is_frozen_and_strict() -> None:
    spec = ToolSpec(
        name="get_order",
        classification=DataClassification.INTERNAL,
        region="cl",
        required_scope="tool:get_order",
    )
    with pytest.raises(ValidationError):
        spec.region = "ve"  # type: ignore[misc]


@pytest.mark.parametrize("name", ["Get-Order", "", "1order"])
def test_tool_name_must_be_an_identifier(name: str) -> None:
    with pytest.raises(ValidationError):
        ToolSpec(
            name=name,
            classification=DataClassification.INTERNAL,
            region="cl",
            required_scope="tool:get_order",
        )


def test_required_scope_must_have_scope_shape() -> None:
    with pytest.raises(ValidationError):
        ToolSpec(
            name="get_order",
            classification=DataClassification.INTERNAL,
            region="cl",
            required_scope="get_order",
        )


def test_result_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        GatewayResult(
            decision=GatewayDecision.ALLOW,
            reason=GatewayReason.OK,
            output="x",
            extra=1,  # type: ignore[call-arg]
        )
