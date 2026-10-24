from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from agent_zero.llm.models import CallKind, CallOrigin, CallOutcome


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CallUsage(FrozenModel):
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cache_read_tokens: int = Field(default=0, ge=0)
    cache_write_tokens: int = Field(default=0, ge=0)

    def __add__(self, other: "CallUsage") -> "CallUsage":
        return CallUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_read_tokens=self.cache_read_tokens + other.cache_read_tokens,
            cache_write_tokens=self.cache_write_tokens + other.cache_write_tokens,
        )

    @property
    def prompt_tokens(self) -> int:
        return self.input_tokens + self.cache_read_tokens + self.cache_write_tokens

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.output_tokens


class CallCost(FrozenModel):
    input_usd: float = Field(default=0.0, ge=0.0)
    output_usd: float = Field(default=0.0, ge=0.0)
    cache_read_usd: float = Field(default=0.0, ge=0.0)
    cache_write_usd: float = Field(default=0.0, ge=0.0)

    def __add__(self, other: "CallCost") -> "CallCost":
        return CallCost(
            input_usd=self.input_usd + other.input_usd,
            output_usd=self.output_usd + other.output_usd,
            cache_read_usd=self.cache_read_usd + other.cache_read_usd,
            cache_write_usd=self.cache_write_usd + other.cache_write_usd,
        )

    @property
    def total_usd(self) -> float:
        return self.input_usd + self.output_usd + self.cache_read_usd + self.cache_write_usd


class TokenPrice(FrozenModel):
    input_usd_per_mtok: float = Field(ge=0.0)
    output_usd_per_mtok: float = Field(ge=0.0)
    cache_read_usd_per_mtok: float = Field(ge=0.0)
    cache_write_usd_per_mtok: float = Field(ge=0.0)


class ModelPrice(FrozenModel):
    standard: TokenPrice
    long_context: TokenPrice | None = None
    long_context_threshold: int | None = Field(default=None, ge=1)

    def for_prompt(self, prompt_tokens: int) -> TokenPrice:
        threshold = self.long_context_threshold
        if self.long_context is not None and threshold is not None and prompt_tokens > threshold:
            return self.long_context
        return self.standard


class CallScope(FrozenModel):
    campaign_id: str | None = None
    session_id: str | None = None
    attempt_id: str | None = None


class CallRecord(FrozenModel):
    call_id: str = Field(min_length=1)
    at: datetime
    role: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    kind: CallKind
    output_model: str | None = None
    origin: CallOrigin
    outcome: CallOutcome
    latency_ms: float = Field(ge=0.0)
    usage: CallUsage | None = None
    cost: CallCost | None = None
    stop_reason: str | None = None
    prompt_version: str | None = None
    scope: CallScope = CallScope()
    error: str = ""

    @property
    def measured(self) -> bool:
        return self.origin is CallOrigin.LIVE
