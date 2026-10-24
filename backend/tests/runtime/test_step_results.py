from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from agent_zero.runtime.step_results import Advance, Complete, Fail, Wait


def test_results_are_frozen_and_strict() -> None:
    advance = Advance(checkpoint={"n": 1})
    with pytest.raises(ValidationError):
        advance.__setattr__("checkpoint", {})
    with pytest.raises(ValidationError):
        Complete(output={}, extra=1)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        Fail(reason="")
    assert Wait(until=datetime(2026, 11, 1, tzinfo=UTC)).checkpoint == {}
