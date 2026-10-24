import re
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from agent_zero.identity.schemas import Scopes
from agent_zero.llm.models import ModelRole
from agent_zero.registry.models import VersionStatus
from agent_zero.registry.semver import SEMVER_PATTERN
from agent_zero.shared.classification import DataClassification

SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
TOOL_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def _check_slug(value: str) -> str:
    if not SLUG_PATTERN.fullmatch(value):
        raise ValueError("Debe ser un identificador en minúsculas con guiones.")
    return value


def _check_semver(value: str) -> str:
    if not SEMVER_PATTERN.fullmatch(value):
        raise ValueError("Debe ser una versión semver estricta (X.Y.Z).")
    return value


def _normalize_labels(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted({v.strip().lower() for v in values if v.strip()}))


Slug = Annotated[str, Field(min_length=1, max_length=80), AfterValidator(_check_slug)]
Semver = Annotated[str, Field(min_length=5, max_length=40), AfterValidator(_check_semver)]
Labels = Annotated[tuple[str, ...], AfterValidator(_normalize_labels)]


class ToolGrant(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1, max_length=80, pattern=TOOL_NAME_PATTERN.pattern)
    description: str = Field(min_length=1, max_length=2000)
    classification: DataClassification


class AgentManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    agent_id: Slug
    version: Semver
    display_name: str = Field(min_length=1, max_length=120)
    department: Slug
    description: str = Field(min_length=1, max_length=2000)
    capabilities: Labels = ()
    tags: Labels = ()
    model_role: ModelRole
    system_prompt: str = Field(min_length=1, max_length=8000)
    tools: tuple[ToolGrant, ...] = ()
    scopes: Scopes = ()
    max_classification: DataClassification
    allowed_regions: Labels = ()


class AgentVersionRead(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    agent_id: str
    version: str
    department: str
    status: VersionStatus
    manifest: AgentManifest
    manifest_sha256: str
    published_at: datetime
    approved_by: str | None = None
    approved_at: datetime | None = None
    deprecated_at: datetime | None = None


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    approved_by: str = Field(min_length=1, max_length=80)


class IntegrityReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    agent_id: str
    version: str
    ok: bool
    expected_sha256: str
    actual_sha256: str
