from typing import Literal

from pydantic import Field

from agent_zero.config import Settings
from agent_zero.llm.models import ModelRole
from agent_zero.llm.schemas import FrozenModel

Effort = Literal["low", "medium", "high", "xhigh", "max"]


class RoleProfile(FrozenModel):
    effort: Effort
    max_tokens: int = Field(ge=256)


ROLE_PROFILES: dict[ModelRole, RoleProfile] = {
    ModelRole.VICTIM: RoleProfile(effort="low", max_tokens=4096),
    ModelRole.DECOY: RoleProfile(effort="low", max_tokens=4096),
    ModelRole.PROBER: RoleProfile(effort="low", max_tokens=4096),
    ModelRole.ANALYZER: RoleProfile(effort="medium", max_tokens=8192),
    ModelRole.PATCHER: RoleProfile(effort="medium", max_tokens=8192),
}


def model_for(role: ModelRole, settings: Settings) -> str:
    return settings.llm_role_models.get(role.value, settings.llm_model)


def profile_for(role: ModelRole) -> RoleProfile:
    return ROLE_PROFILES[role]
