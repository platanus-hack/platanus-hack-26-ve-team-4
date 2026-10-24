import pytest
from pydantic import ValidationError

from agent_zero.memory_bank.models import MemoryKind
from agent_zero.memory_bank.schemas import MemoryWriteRequest


def test_request_rejects_empty_content_and_extra_fields() -> None:
    with pytest.raises(ValidationError):
        MemoryWriteRequest(subject_id="s", kind=MemoryKind.FACT, content="", source_run_id="r")
    with pytest.raises(ValidationError):
        MemoryWriteRequest.model_validate(
            {"subject_id": "s", "kind": "fact", "content": "x", "source_run_id": "r", "otro": 1}
        )
