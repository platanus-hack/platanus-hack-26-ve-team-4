from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from agent_zero.attempts.models import Attempt, AttemptOrigin, AttemptOutcome, AttemptStatus
from agent_zero.routing.models import Route

MAX_TURNS = 4
MAX_TURN_CHARS = 4000

Turn = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_TURN_CHARS)
]
PublicOutcome = Literal["apparent_success", "prevented", "not_achieved", "inconclusive"]


class AttemptCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: Turn | None = None
    messages: list[Turn] | None = Field(default=None, min_length=1, max_length=MAX_TURNS)
    objective_id: str | None = Field(default=None, min_length=1, max_length=40)
    idempotency_key: str = Field(min_length=8, max_length=120, pattern=r"^[A-Za-z0-9_\-:.]+$")

    @model_validator(mode="after")
    def _one_form_of_messages(self) -> Self:
        if (self.message is None) == (self.messages is None):
            raise ValueError("Envía `message` o `messages`, no ambos ni ninguno.")
        return self

    @property
    def turns(self) -> list[str]:
        return [self.message] if self.message is not None else list(self.messages or [])


def public_outcome(outcome: AttemptOutcome | None) -> PublicOutcome | None:
    """Mientras la ronda no se revela, un éxito en el señuelo y uno real se ven iguales."""
    if outcome in (AttemptOutcome.CONFIRMED_VIOLATION, AttemptOutcome.CONTAINED_HONEYPOT):
        return "apparent_success"
    return None if outcome is None else outcome.value  # type: ignore[return-value]


class AttemptPublicView(BaseModel):
    id: str
    status: AttemptStatus
    outcome: PublicOutcome | None
    messages: list[str]
    reply: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def of(cls, attempt: Attempt) -> Self:
        return cls(
            id=attempt.id,
            status=attempt.status,
            outcome=public_outcome(attempt.outcome),
            messages=list(attempt.messages),
            reply=attempt.reply,
            created_at=attempt.created_at,
            updated_at=attempt.updated_at,
        )


class AttemptOperatorView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    origin: AttemptOrigin
    idempotency_key: str
    messages: list[str]
    objective_id: str | None
    policy_version: int
    route: Route
    run_id: str | None
    status: AttemptStatus
    outcome: AttemptOutcome | None
    reply: str | None
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime
