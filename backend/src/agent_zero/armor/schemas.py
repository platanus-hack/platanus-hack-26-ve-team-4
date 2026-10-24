from pydantic import BaseModel, ConfigDict, Field

from agent_zero.armor.models import ArmorAction, Surface, ThreatKind


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArmorFinding(FrozenModel):
    kind: ThreatKind
    surface: Surface
    detail: str = Field(min_length=1)


class ArmorVerdict(FrozenModel):
    action: ArmorAction
    findings: tuple[ArmorFinding, ...] = ()
    sanitized_text: str | None = None

    @property
    def blocked(self) -> bool:
        return self.action is ArmorAction.BLOCK
