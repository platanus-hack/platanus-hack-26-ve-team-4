from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from itertools import count

import pytest

from agent_zero.config import Settings
from agent_zero.contract.conditions import CallFacts, Exceeds, WindowExceeds
from agent_zero.contract.schema import PolicyRule
from agent_zero.guard.facts import dump
from agent_zero.guard.models import GuardCallRecord
from agent_zero.guard.window_totals import window_conditions, window_totals
from agent_zero.shared.database import Database
from tests.contract.support import shipped

BANK = shipped()["banco-transferencias"]
DAILY = WindowExceeds(kind="window_exceeds", argument="monto", limit=1000, window_seconds=86400)
IDS = count()


@pytest.fixture
async def database(settings: Settings) -> AsyncIterator[Database]:
    db = Database(settings.app_database_url)
    await db.create_schema()
    yield db
    await db.dispose()


def record(
    amount: float,
    *,
    age: int = 60,
    subject: str = "ana",
    tool: str = "transferir",
    allowed: bool = True,
) -> GuardCallRecord:
    facts = CallFacts(tool, {"monto": amount}, subject)
    return GuardCallRecord(
        call_id=f"gc-{next(IDS)}",
        contract_id=BANK.contract_id,
        tool=tool,
        subject=subject,
        facts=dump(facts),
        allowed=allowed,
        policy_version=0,
        created_at=datetime.now(UTC) - timedelta(seconds=age),
    )


async def total(database: Database) -> float:
    async with database.sessions() as db:
        found = await window_totals(db, BANK.contract_id, "ana", "transferir", [DAILY])
    return found[DAILY.total_key()]


async def test_only_allowed_calls_of_the_subject_and_tool_inside_the_window_count(
    database: Database,
) -> None:
    async with database.sessions() as db, db.begin():
        db.add_all(
            [
                record(450),
                record(300, age=86000),
                record(900, age=86401),
                record(900, subject="bruno"),
                record(900, allowed=False),
                record(900, tool="consultar_saldo"),
            ]
        )
    assert await total(database) == 750


async def test_an_empty_history_sums_to_zero(database: Database) -> None:
    assert await total(database) == 0


def test_window_conditions_come_from_invariants_and_rules_without_duplicates() -> None:
    assert window_conditions(BANK, "transferir", []) == [DAILY]
    assert window_conditions(BANK, "consultar_saldo", []) == []
    hourly = WindowExceeds(kind="window_exceeds", argument="monto", limit=5, window_seconds=3600)
    rules = [
        PolicyRule(rule_id="r_a", tool="transferir", deny_when=hourly, reason="x"),
        PolicyRule(rule_id="r_b", tool="transferir", deny_when=DAILY, reason="x"),
        PolicyRule(
            rule_id="r_c",
            tool="transferir",
            deny_when=Exceeds(kind="exceeds", argument="monto", limit=1),
            reason="x",
        ),
    ]
    assert window_conditions(BANK, "transferir", rules) == [DAILY, hourly]
