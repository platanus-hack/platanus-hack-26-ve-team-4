from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from opentelemetry.sdk.trace import ReadableSpan

from agent_zero.fleet.fleet_builder import Fleet
from agent_zero.fleet.schemas import (
    AuditReport,
    FleetStatus,
    RevocationReport,
    RunTrace,
    SpanView,
)
from agent_zero.identity.revocation_service import RevocationService
from agent_zero.llm.gateway import LlmGateway
from agent_zero.runtime.repository import RunRepository
from agent_zero.shared.dependencies import DbSession
from agent_zero.shared.operator_auth import OperatorOnly
from agent_zero.telemetry.audit_schemas import AuditDecision, AuditEvent

router = APIRouter(prefix="/api/fleet", tags=["fleet"], dependencies=[OperatorOnly])


def _fleet(request: Request) -> Fleet:
    fleet: Fleet = request.app.state.fleet
    return fleet


def _llm(request: Request) -> LlmGateway:
    llm: LlmGateway = request.app.state.llm
    return llm


FleetDep = Annotated[Fleet, Depends(_fleet)]
LlmDep = Annotated[LlmGateway, Depends(_llm)]


def _view(span: ReadableSpan) -> SpanView:
    context = span.get_span_context()
    return SpanView(
        name=span.name,
        trace_id=f"{context.trace_id:032x}" if context else "",
        span_id=f"{context.span_id:016x}" if context else "",
        parent_id=f"{span.parent.span_id:016x}" if span.parent else None,
        status=span.status.status_code.name,
        attributes=dict(span.attributes or {}),
    )


@router.get("/status")
async def fleet_status(fleet: FleetDep, llm: LlmDep) -> FleetStatus:
    settings = fleet.settings
    return FleetStatus(
        environment=settings.environment,
        llm_mode=llm.mode.value,
        llm_spent_today_usd=round(llm.limits.spent_today_usd(), 6),
        llm_daily_usd_limit=settings.llm_daily_usd_limit,
        otel_exporter=settings.otel_exporter,
        handlers=fleet.handlers.names(),
        tools=fleet.tools.names(),
    )


@router.get("/runs/{run_id}/trace")
async def run_trace(run_id: str, db: DbSession, fleet: FleetDep) -> RunTrace:
    exporter = fleet.telemetry.memory_exporter
    if exporter is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "La traza solo se sirve con AGENT_ZERO_OTEL_EXPORTER=memory; "
            "con otlp, consúltala en el colector.",
        )
    run = await RunRepository(db).get(run_id)
    if run is None or run.trace_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No hay traza para la ejecución {run_id}.")
    spans = [_view(span) for span in exporter.get_finished_spans()]
    return RunTrace(
        run_id=run_id,
        trace_id=run.trace_id,
        spans=tuple(span for span in spans if span.trace_id == run.trace_id),
    )


@router.get("/audit")
async def audit_report(
    fleet: FleetDep, limit: Annotated[int, Query(ge=1, le=200)] = 20
) -> AuditReport:
    return AuditReport(
        verification=fleet.audit.verify(), latest=tuple(fleet.audit.entries()[-limit:])
    )


@router.post("/agents/{agent_id}/revoke")
async def revoke_agent(agent_id: str, db: DbSession, fleet: FleetDep) -> RevocationReport:
    await RevocationService(db, fleet.clock).revoke_agent(agent_id)
    fleet.audit.append(
        AuditEvent(
            actor="operador",
            action="identity.revoke_agent",
            resource=f"agent:{agent_id}",
            decision=AuditDecision.INFO,
        )
    )
    return RevocationReport(agent_id=agent_id, revoked=True)
