from typing import Any

from pydantic import BaseModel, ConfigDict

from agent_zero.telemetry.audit_schemas import AuditEntry, AuditVerification


class FleetStatus(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    environment: str
    llm_mode: str
    llm_spent_today_usd: float
    llm_daily_usd_limit: float
    otel_exporter: str
    handlers: tuple[str, ...]
    tools: tuple[str, ...]


class SpanView(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    trace_id: str
    span_id: str
    parent_id: str | None
    status: str
    attributes: dict[str, Any]


class RunTrace(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    trace_id: str
    spans: tuple[SpanView, ...]


class AuditReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    verification: AuditVerification
    latest: tuple[AuditEntry, ...]


class RevocationReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    agent_id: str
    revoked: bool
