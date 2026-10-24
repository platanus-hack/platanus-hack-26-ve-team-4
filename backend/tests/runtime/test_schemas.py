import pytest
from pydantic import ValidationError

from agent_zero.runtime.schemas import RunCreate


def test_run_create_rejects_unknown_and_empty_fields() -> None:
    with pytest.raises(ValidationError):
        RunCreate(agent_id="", agent_version="1", handler="h")
    with pytest.raises(ValidationError):
        RunCreate(agent_id="a", agent_version="1", handler="h", otro=1)  # type: ignore[call-arg]
    created = RunCreate(agent_id="a", agent_version="1", handler="h")
    assert created.input == {}
    assert created.idempotency_key is None
