import pytest

from agent_zero.agent_gateway.errors import (
    DuplicateToolError,
    GatewayDeniedError,
    ToolExecutionError,
)
from agent_zero.agent_gateway.models import GatewayReason, GatewayStage


@pytest.mark.parametrize(
    "reason",
    [
        reason
        for reason in GatewayReason
        if reason.name.startswith(
            ("IDENTITY", "TOOL_", "REGION", "RATE", "AGENT", "CLASS", "INPUT_B", "OUTPUT_B")
        )
    ],
)
def test_denials_have_spanish_messages(reason: GatewayReason) -> None:
    error = GatewayDeniedError(reason, GatewayStage.POLICY)
    assert str(error).startswith("Llamada denegada por el gateway:")
    assert error.reason is reason
    assert error.stage is GatewayStage.POLICY


def test_tool_execution_error_keeps_the_original() -> None:
    original = ValueError("detalle sensible")
    error = ToolExecutionError(original)
    assert error.original is original
    assert "detalle sensible" not in str(error)


def test_duplicate_error_names_the_tool() -> None:
    assert DuplicateToolError("x").name == "x"
