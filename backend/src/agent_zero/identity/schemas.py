import re
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from agent_zero.shared.classification import DataClassification

SCOPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*:[a-z][a-z0-9_]*$")


def _normalize_scopes(scopes: tuple[str, ...]) -> tuple[str, ...]:
    for scope in scopes:
        if not SCOPE_PATTERN.fullmatch(scope):
            raise ValueError(f"Permiso con forma inválida: {scope}")
    return tuple(sorted(set(scopes)))


Scopes = Annotated[tuple[str, ...], AfterValidator(_normalize_scopes)]


class AgentGrant(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    agent_id: str = Field(min_length=1, max_length=80)
    version: str = Field(min_length=1, max_length=40)
    department: str = Field(min_length=1, max_length=80)
    scopes: Scopes = ()
    clearance: DataClassification
    allowed_regions: tuple[str, ...] = ()


class AgentPrincipal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    credential_id: str
    agent_id: str
    version: str
    department: str
    scopes: Scopes
    clearance: DataClassification
    allowed_regions: tuple[str, ...]
    issued_at: datetime
    expires_at: datetime


class IssuedCredential(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    token: str
    principal: AgentPrincipal
