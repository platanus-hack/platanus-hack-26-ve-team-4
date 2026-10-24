from collections.abc import Callable

PREFIX = "agent_zero."

RUN_ID = "agent_zero.run_id"
AGENT_ID = "agent_zero.agent_id"
STEP = "agent_zero.step"
DECISION = "agent_zero.decision"
TOOL = "agent_zero.tool"
MODEL = "agent_zero.model"
ACTOR = "agent_zero.actor"

Redactor = Callable[[str], str]


def identity_redactor(text: str) -> str:
    return text


def namespaced(key: str) -> str:
    return key if key.startswith(PREFIX) else f"{PREFIX}{key}"
