from agent_zero.walkthrough.client import FleetClient
from agent_zero.walkthrough.observability_steps import check_audit, check_trace
from agent_zero.walkthrough.registry_steps import check_platform, check_registry
from agent_zero.walkthrough.report import Report
from agent_zero.walkthrough.run_steps import (
    check_first_contact,
    check_injection,
    check_revocation,
    check_second_contact,
)


def run_walkthrough(
    client: FleetClient, follow_up_seconds: int = 5, run_timeout: float = 90.0
) -> Report:
    report = Report()
    check_platform(client, report)
    check_registry(client, report)
    first = check_first_contact(client, report, follow_up_seconds, run_timeout)
    check_second_contact(client, report, run_timeout)
    check_injection(client, report, run_timeout)
    check_revocation(client, report, run_timeout)
    check_trace(client, report, first)
    check_audit(client, report)
    return report
