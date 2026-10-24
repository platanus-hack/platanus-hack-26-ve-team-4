import asyncio
from collections.abc import AsyncIterator

import pytest

from agent_zero.config import Settings
from agent_zero.guard.check_service import GuardCheckService
from agent_zero.guard.schemas import CheckRequest
from agent_zero.shared.database import Database
from tests.contract.support import shipped

BANK = shipped()["banco-transferencias"]


def rent(subject: str = "ana") -> CheckRequest:
    return CheckRequest.model_validate(
        {
            "subject": subject,
            "tool": "transferir",
            "arguments": {
                "cuenta": "CTA-1",
                "destino": "BEN-ALQUILER",
                "monto": 450,
                "concepto": "alquiler",
            },
            "provenance": {
                "cuenta": "user",
                "destino": "user",
                "monto": "user",
                "concepto": "user",
            },
            "owners": {"cuenta": subject},
        }
    )


@pytest.fixture
async def checks(settings: Settings) -> AsyncIterator[GuardCheckService]:
    database = Database(settings.app_database_url)
    await database.create_schema()
    yield GuardCheckService(database)
    await database.dispose()


async def test_concurrent_checks_cannot_overrun_the_daily_window(
    checks: GuardCheckService,
) -> None:
    decisions = await asyncio.gather(*(checks.check(BANK, rent()) for _ in range(4)))
    allowed = [decision for decision in decisions if decision.allowed]
    blocked = [decision for decision in decisions if not decision.allowed]
    assert len(allowed) == 2
    assert {decision.rule_id for decision in blocked} == {"invariant:tope-diario"}


async def test_each_subject_has_its_own_window(checks: GuardCheckService) -> None:
    for _ in range(2):
        assert (await checks.check(BANK, rent())).allowed
    assert (await checks.check(BANK, rent("bruno"))).allowed
    assert not (await checks.check(BANK, rent())).allowed
