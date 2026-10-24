from agent_zero.llm.context import (
    call_scope,
    current_scope,
    declared_prompt_version,
    declaring_prompt_version,
)
from agent_zero.llm.schemas import CallScope


def test_nested_scopes_inherit_and_restore() -> None:
    with call_scope(campaign_id="camp-1"):
        with call_scope(attempt_id="att-1") as inner:
            assert inner == CallScope(campaign_id="camp-1", attempt_id="att-1")
        assert current_scope() == CallScope(campaign_id="camp-1")

    assert current_scope() == CallScope()


def test_prompt_version_is_scoped() -> None:
    with declaring_prompt_version("prober-v1"):
        assert declared_prompt_version() == "prober-v1"

    assert declared_prompt_version() is None
