import json
from pathlib import Path

import pytest

from agent_zero.agent_gateway.schemas import ToolSpec
from agent_zero.config import Settings
from agent_zero.fleet.fleet_builder import Fleet, build_fleet
from agent_zero.runtime.models import RunStatus
from agent_zero.shared.classification import DataClassification
from agent_zero.shared.database import Database
from agent_zero.telemetry.audit_schemas import AuditDecision
from agent_zero.telemetry.otel_setup import Telemetry, build_telemetry
from tests.agent_gateway.support import ORDER_OUTPUT, build_manifest, grants
from tests.fleet.support import drain, enqueue_run, load_run, publish_approved
from tests.fleet.support_handler import SupportFollowUpHandler
from tests.identity.conftest import FakeClock

EMAIL = "cliente@example.com"


async def order_tool(arguments: dict[str, object]) -> str:
    return ORDER_OUTPUT


async def start_fleet(
    settings: Settings, clock: FakeClock, telemetry: Telemetry
) -> tuple[Fleet, SupportFollowUpHandler]:
    database = Database(settings.app_database_url)
    await database.create_schema()
    fleet = build_fleet(settings, database, clock, telemetry)
    fleet.tools.register(
        ToolSpec(
            name="get_order",
            classification=DataClassification.INTERNAL,
            region="cl",
            required_scope="tool:get_order",
        ),
        order_tool,
    )
    handler = SupportFollowUpHandler(fleet)
    fleet.handlers.register(handler)
    return fleet, handler


@pytest.mark.requirement("E2E-01")
async def test_support_agent_survives_two_weeks_and_a_restart(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path,
        environment="test",
        identity_signing_key="clave-de-prueba",
        otel_exporter="memory",
    )
    clock = FakeClock()
    telemetry = build_telemetry(settings)

    first, first_handler = await start_fleet(settings, clock, telemetry)
    manifest = build_manifest(
        tools=grants("get_order"), scopes=("tool:get_order", "memory:read", "memory:write")
    )
    await publish_approved(first, manifest)
    run_id = await enqueue_run(first, "agente-soporte", first_handler.name)
    await drain(first)
    waiting = await load_run(first, run_id)
    assert waiting.status is RunStatus.WAITING
    assert waiting.resume_at is not None
    assert first_handler.steps == [0]
    await first.stop()
    await first.database.dispose()

    clock.advance(seconds=15 * 86400)
    second, second_handler = await start_fleet(settings, clock, telemetry)
    await drain(second)
    done = await load_run(second, run_id)
    assert done.status is RunStatus.SUCCEEDED
    assert second_handler.steps == [1]
    assert done.output_json is not None
    assert done.output_json["injection_blocked_as"] == "input_blocked"
    assert done.output_json["recalled_run_ids"] == [run_id]
    assert "[EMAIL]" in done.output_json["order"]
    assert EMAIL not in json.dumps(done.output_json)
    assert "[EMAIL]" in done.output_json["recalled"][0]

    assert telemetry.memory_exporter is not None
    spans = telemetry.memory_exporter.get_finished_spans()
    names = {span.name.removeprefix("agent_zero.") for span in spans}
    assert {"runtime.run", "runtime.step", "gateway.call_tool", "gateway.audit"} <= names
    trace_ids = {format(span.context.trace_id, "032x") for span in spans if span.context}
    assert trace_ids == {done.trace_id}
    for span in spans:
        flattened = json.dumps(dict(span.attributes or {}), default=str)
        flattened += json.dumps([dict(e.attributes or {}) for e in span.events], default=str)
        assert EMAIL not in flattened

    verification = second.audit.verify()
    assert verification.ok
    entries = second.audit.entries()
    assert [e.reason for e in entries] == ["output_pii_redacted", "input_blocked"]
    assert [e.decision for e in entries] == [AuditDecision.ALLOW, AuditDecision.DENY]
    assert entries[0].attributes["gateway_decision"] == "redact"
    assert {e.trace_id for e in entries} == {done.trace_id}
    assert EMAIL not in settings.audit_log_path.read_text(encoding="utf-8")
    await second.stop()
    await second.database.dispose()
    telemetry.shutdown()
