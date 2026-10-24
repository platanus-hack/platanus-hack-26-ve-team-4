from typing import Any

import pytest

from agent_zero.agent_gateway.errors import DuplicateToolError
from agent_zero.agent_gateway.schemas import ToolSpec
from agent_zero.agent_gateway.tool_registry import ToolRegistry
from agent_zero.shared.classification import DataClassification


async def handler(arguments: dict[str, Any]) -> str:
    return "ok"


def spec(name: str) -> ToolSpec:
    return ToolSpec(
        name=name,
        classification=DataClassification.INTERNAL,
        region="cl",
        required_scope=f"tool:{name}",
    )


def test_register_and_lookup() -> None:
    registry = ToolRegistry()
    registry.register(spec("b_tool"), handler)
    registry.register(spec("a_tool"), handler)
    assert registry.names() == ("a_tool", "b_tool")
    found = registry.get("a_tool")
    assert found is not None
    assert found.spec.name == "a_tool"
    assert registry.get("missing") is None


def test_duplicate_name_is_rejected_in_spanish() -> None:
    registry = ToolRegistry()
    registry.register(spec("a_tool"), handler)
    with pytest.raises(DuplicateToolError, match="Ya existe una herramienta"):
        registry.register(spec("a_tool"), handler)
