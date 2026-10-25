import unicodedata
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agent_zero.oracles.schemas import ObjectiveId

Message = Annotated[str, Field(min_length=1, max_length=4000)]


def is_blank(text: str) -> bool:
    return all(char.isspace() or unicodedata.category(char) == "Cf" for char in text)


class AttemptCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: Message | None = None
    messages: list[Message] | None = Field(default=None, min_length=1, max_length=4)
    objective_id: ObjectiveId | None = None
    idempotency_key: str = Field(min_length=1, max_length=120)
    # Intento previo de la misma sesión cuya conversación continúa este (chat del participante).
    continues: str | None = Field(default=None, min_length=1, max_length=40)

    @model_validator(mode="after")
    def exactly_one_message_form(self) -> Self:
        if (self.message is None) == (self.messages is None):
            raise ValueError("Envía message o messages, exactamente uno.")
        if any(is_blank(message) for message in self.turns):
            raise ValueError("Los mensajes no pueden estar vacíos.")
        return self

    @property
    def turns(self) -> list[str]:
        return self.messages if self.messages is not None else [self.message or ""]


PublicOutcome = Literal["apparent_success", "prevented", "not_achieved", "inconclusive"]
