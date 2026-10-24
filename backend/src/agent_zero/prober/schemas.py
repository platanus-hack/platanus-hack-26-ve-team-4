from pydantic import BaseModel, Field

from agent_zero.prober.models import AttackFamily, AttackOrigin, Surface


class AttackCase(BaseModel):
    case_id: str
    family: AttackFamily
    surface: Surface
    objective_id: str
    messages: list[str] = Field(min_length=1, max_length=4)
    fixture_id: str
    seed: int | None = None
    parent_case_id: str | None = None
    origin: AttackOrigin
