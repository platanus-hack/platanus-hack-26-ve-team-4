import pytest

from agent_zero.runtime.handler_registry import HandlerRegistry, UnknownHandlerError
from agent_zero.runtime.step_results import Complete
from tests.runtime.support import ScriptedHandler


async def _done(_context: object) -> Complete:
    return Complete()


def test_register_and_lookup_by_name() -> None:
    registry = HandlerRegistry()
    handler = ScriptedHandler("uno", [_done])
    registry.register(handler)
    assert registry.get("uno") is handler
    assert registry.names() == ("uno",)


def test_unknown_handler_raises_spanish_error() -> None:
    with pytest.raises(UnknownHandlerError, match="No existe un manejador"):
        HandlerRegistry().get("nada")
