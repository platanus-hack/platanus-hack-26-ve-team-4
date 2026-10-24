"""Contrato de la traza de herramientas (v2). Ver docs/dominio/traza-herramientas.md.

`TraceObserver` escribe estos modelos en `data` de cada evento `tool_*`; los oráculos los leen con
`oracles.assessment_service.tool_evidence`. Cambiar un campo es cambiar lo que leen los oráculos.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

TRACE_SCHEMA_VERSION: Literal[2] = 2


class _Effect(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class NoEffect(_Effect):
    kind: Literal["none"] = "none"


class ReadEffect(_Effect):
    kind: Literal["read"] = "read"
    order_id: str
    owner_customer_id: str


class RefundEffect(_Effect):
    kind: Literal["refund"] = "refund"
    order_id: str
    owner_customer_id: str
    amount_cents: int
    refunded_before_cents: int
    refunded_after_cents: int
    total_cents: int


class MemoryEffect(_Effect):
    kind: Literal["memory_write"] = "memory_write"
    memory_id: str
    key: str
    value: str


ToolEffect = Annotated[
    NoEffect | ReadEffect | RefundEffect | MemoryEffect, Field(discriminator="kind")
]


class TraceData(BaseModel):
    """Campos comunes a los cuatro eventos; el contexto lo fija el servidor, no el modelo."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[2] = TRACE_SCHEMA_VERSION
    tool: str
    arguments: dict[str, Any]
    environment: str
    session_customer_id: str
    operation_id: str
    # Origen de cada argumento (`victim.provenance`): lo usan las reglas de flujo y la síntesis.
    provenance: dict[str, str] = Field(default_factory=dict)


class ProposedData(TraceData):
    pass


class DeniedData(TraceData):
    stage: str
    reason: str
    validator: str | None = None
    detail: str | None = None
    data_region: str | None = None


class CompletedData(TraceData):
    # None sólo si el adaptador no devolvió un objeto JSON o no declaró su efecto: los
    # oráculos tratan esa traza como ilegible y el intento queda inconcluso.
    output: dict[str, Any] | None
    effect: ToolEffect | None


class FailedData(TraceData):
    stage: Literal["tool"] = "tool"
    reason: Literal["tool_failed"] = "tool_failed"
    error: str


TRACE_DATA: dict[str, type[TraceData]] = {
    "tool_proposed": ProposedData,
    "tool_denied": DeniedData,
    "tool_completed": CompletedData,
    "tool_failed": FailedData,
}
