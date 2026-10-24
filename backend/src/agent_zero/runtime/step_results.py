from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Advance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    checkpoint: dict[str, Any] = Field(default_factory=dict)


class Wait(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    until: datetime
    checkpoint: dict[str, Any] = Field(default_factory=dict)


class Complete(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    output: dict[str, Any] = Field(default_factory=dict)


class Fail(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    reason: str = Field(min_length=1)


StepResult = Advance | Wait | Complete | Fail
