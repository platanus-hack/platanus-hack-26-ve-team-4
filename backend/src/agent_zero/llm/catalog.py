from typing import Literal

from pydantic import Field

from agent_zero.config import Settings
from agent_zero.llm.models import ModelRole
from agent_zero.llm.schemas import FrozenModel

Effort = Literal["low", "medium", "high", "xhigh", "max"]
Thinking = Literal["adaptive", "disabled"]


class RoleProfile(FrozenModel):
    effort: Effort
    thinking: Thinking
    max_tokens: int = Field(ge=256)


ROLE_PROFILES: dict[ModelRole, RoleProfile] = {
    ModelRole.VICTIM: RoleProfile(effort="low", thinking="disabled", max_tokens=2048),
    ModelRole.DECOY: RoleProfile(effort="low", thinking="disabled", max_tokens=2048),
    ModelRole.PROBER: RoleProfile(effort="low", thinking="disabled", max_tokens=2048),
    ModelRole.ANALYZER: RoleProfile(effort="medium", thinking="adaptive", max_tokens=8192),
    ModelRole.PATCHER: RoleProfile(effort="medium", thinking="adaptive", max_tokens=8192),
}


def model_for(role: ModelRole, settings: Settings) -> str:
    return settings.llm_role_models.get(role.value, settings.llm_model)


def profile_for(role: ModelRole) -> RoleProfile:
    return ROLE_PROFILES[role]
