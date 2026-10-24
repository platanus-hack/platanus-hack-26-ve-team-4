from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from agent_zero.routing.models import Route


class SessionCreate(BaseModel):
    # extra="forbid": la identidad del cliente la asigna el servidor; un customer_id enviado es 422.
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


class SessionOperatorView(SessionRead):
    customer_id: str
    route: Route
