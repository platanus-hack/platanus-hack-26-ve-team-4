from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from agent_zero.llm.schemas import CallScope

_scope: ContextVar[CallScope | None] = ContextVar("agent_zero_llm_scope", default=None)
_prompt_version: ContextVar[str | None] = ContextVar("agent_zero_prompt_version", default=None)


def current_scope() -> CallScope:
    return _scope.get() or CallScope()


@contextmanager
def call_scope(
    *,
    campaign_id: str | None = None,
    session_id: str | None = None,
    attempt_id: str | None = None,
) -> Iterator[CallScope]:
    parent = current_scope()
    scope = CallScope(
        campaign_id=campaign_id or parent.campaign_id,
        session_id=session_id or parent.session_id,
        attempt_id=attempt_id or parent.attempt_id,
    )
    token = _scope.set(scope)
    try:
        yield scope
    finally:
        _scope.reset(token)


@contextmanager
def declaring_prompt_version(version: str) -> Iterator[None]:
    token = _prompt_version.set(version)
    try:
        yield
    finally:
        _prompt_version.reset(token)


def declared_prompt_version() -> str | None:
    return _prompt_version.get()
