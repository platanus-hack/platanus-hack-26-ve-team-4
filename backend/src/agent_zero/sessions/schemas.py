from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    alias: str = Field(min_length=2, max_length=40, pattern=r"^[\w\- ]+$")
    accepted_rules: Literal[True]


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    alias: str
    created_at: datetime


class SessionIssued(SessionRead):
    token: str
    expires_at: datetime
    customer_name: str
    order_ids: list[str]
    objectives: list[str]
