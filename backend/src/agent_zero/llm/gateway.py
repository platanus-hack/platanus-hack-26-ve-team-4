from collections.abc import Mapping
from typing import TypeVar

from pydantic import BaseModel
from strands.models.model import Model
from strands.types.content import Messages

from agent_zero.llm.ledger import CallLedger
from agent_zero.llm.limits import ModelLimits
from agent_zero.llm.models import LlmMode, ModelRole
from agent_zero.llm.reporting import RoleUsage, summarize
from agent_zero.llm.structured import DEFAULT_REPAIR_BUDGET, structured_call

T = TypeVar("T", bound=BaseModel)


class LlmGateway:
    def __init__(
        self,
        mode: LlmMode,
        models: Mapping[ModelRole, Model],
        ledger: CallLedger,
        limits: ModelLimits,
    ) -> None:
        missing = set(ModelRole) - set(models)
        if missing:
            raise ValueError(f"faltan modelos para los roles {sorted(missing)}")
        self.mode = mode
        self.ledger = ledger
        self.limits = limits
        self._models = dict(models)

    def model(self, role: ModelRole) -> Model:
        return self._models[role]

    async def structured(
        self,
        role: ModelRole,
        output_model: type[T],
        prompt: Messages,
        system_prompt: str | None = None,
        repair_budget: int = DEFAULT_REPAIR_BUDGET,
    ) -> T:
        return await structured_call(
            self.model(role), output_model, prompt, system_prompt, repair_budget
        )

    def usage(self) -> list[RoleUsage]:
        return summarize(self.ledger.records())
