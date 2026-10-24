from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agent_zero.prober.models import AttackFamily, AttackOrigin, Surface
from agent_zero.victim.controlled_fixtures import ControlledFixture

AttackMessage = Annotated[str, Field(min_length=1, max_length=4000)]


class AttackCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(min_length=1, max_length=120)
    family: AttackFamily
    surface: Surface
    objective_id: Literal["OBJ-ORDER", "OBJ-REFUND", "OBJ-MEMORY"]
    messages: list[AttackMessage] = Field(min_length=1, max_length=4)
    fixture_id: Literal["tienda"]
    fixture: ControlledFixture | None = None
    seed: int | None = None
    parent_case_id: str | None = None
    origin: AttackOrigin

    @model_validator(mode="after")
    def surface_matches_fixture(self) -> Self:
        if self.surface in {Surface.DOCUMENT, Surface.TOOL_RESULT}:
            if self.fixture is None or self.fixture.surface != self.surface.value:
                raise ValueError("La superficie necesita un fixture controlado del mismo tipo.")
        elif self.fixture is not None:
            raise ValueError("Un mensaje o memoria no admite fixtures de otras superficies.")
        if any(not message.strip() for message in self.messages):
            raise ValueError("Los mensajes no pueden estar vacíos.")
        return self


class AttackMutation(BaseModel):
    """The model can change text; identity, objective and controls stay server-owned."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    messages: list[AttackMessage] = Field(min_length=1, max_length=4)
    fixture_content: str | None = Field(default=None, min_length=1, max_length=8000)

    @model_validator(mode="after")
    def nonempty_messages(self) -> Self:
        if any(not message.strip() for message in self.messages):
            raise ValueError("Los mensajes no pueden estar vacíos.")
        return self
