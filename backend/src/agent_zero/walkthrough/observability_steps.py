import json
from typing import Any

from agent_zero.walkthrough.client import FleetClient
from agent_zero.walkthrough.report import Report
from agent_zero.walkthrough.run_steps import CUSTOMER_EMAIL

MODEL_SPAN = "agent_zero.model.call"
GATEWAY_SPAN_PREFIX = "agent_zero.gateway"


def check_trace(client: FleetClient, report: Report, run: dict[str, Any]) -> None:
    response = client.get(f"/api/fleet/runs/{run['run_id']}/trace")
    if response.status_code != 200:
        report.add("Observability", "traza del run", False, response.json().get("detail"))
        return
    trace = response.json()
    spans = trace["spans"]
    names = sorted({span["name"] for span in spans})
    report.add(
        "Observability",
        "una sola traza con run, gateway y modelo",
        bool(spans)
        and {span["trace_id"] for span in spans} == {trace["trace_id"]}
        and MODEL_SPAN in names
        and any(name.startswith(GATEWAY_SPAN_PREFIX) for name in names),
        f"{len(spans)} spans: {names}",
    )
    leaked = CUSTOMER_EMAIL in json.dumps([span["attributes"] for span in spans])
    report.add("Observability", "sin PII en atributos de los spans", not leaked)


def check_audit(client: FleetClient, report: Report) -> None:
    audit = client.get("/api/fleet/audit", limit=200).json()
    verification = audit["verification"]
    report.add(
        "Observability",
        "cadena de auditoría firmada e íntegra",
        verification["ok"] is True,
        f"{verification['entries']} entradas",
    )
    denials = [entry for entry in audit["latest"] if entry["decision"] == "deny"]
    report.add(
        "Observability",
        "las negaciones del gateway quedan auditadas",
        any(entry["reason"] for entry in denials),
        sorted({entry["reason"] for entry in denials}),
    )
    status = client.get("/api/fleet/status").json()
    report.add(
        "Plataforma",
        "gasto del día dentro del tope",
        status["llm_spent_today_usd"] <= status["llm_daily_usd_limit"],
        f"US$ {status['llm_spent_today_usd']:.6f} de {status['llm_daily_usd_limit']}",
    )
