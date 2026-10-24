from datetime import UTC, date, datetime

import pytest

from agent_zero.llm.errors import ModelLimitReachedError
from agent_zero.llm.limits import LimitPolicy, ModelLimits
from agent_zero.llm.models import CallOrigin, LimitReason
from agent_zero.llm.quota import InMemoryCallQuota
from agent_zero.llm.schemas import CallCost, CallScope, CallUsage
from tests.llm.records import call_record


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def build_limits(clock: FakeClock, **overrides: float) -> ModelLimits:
    values: dict[str, float] = {
        "daily_calls": 100,
        "session_calls": 100,
        "campaign_calls": 100,
        "campaign_tokens": 1_000,
        "daily_usd": 1.0,
        "breaker_failures": 2,
        "breaker_recovery_seconds": 30,
        **overrides,
    }
    policy = LimitPolicy.model_validate(values)
    return ModelLimits(policy, InMemoryCallQuota(), clock, lambda: date(2026, 10, 24))


def reason_of(limits: ModelLimits, scope: CallScope) -> LimitReason:
    with pytest.raises(ModelLimitReachedError) as denial:
        limits.before("prober", scope)
    return denial.value.reason


def test_session_ceiling_denies_the_next_call() -> None:
    limits = build_limits(FakeClock(), session_calls=1)
    scope = CallScope(session_id="sess-1")
    limits.before("victim", scope)

    assert reason_of(limits, scope) is LimitReason.SESSION_CEILING
    limits.before("victim", CallScope(session_id="sess-2"))


def test_daily_ceiling_applies_without_scope() -> None:
    limits = build_limits(FakeClock(), daily_calls=1)
    limits.before("prober", CallScope())

    assert reason_of(limits, CallScope()) is LimitReason.DAILY_CEILING


def test_campaign_token_budget_is_charged_after_each_call() -> None:
    limits = build_limits(FakeClock(), campaign_tokens=100)
    scope = CallScope(campaign_id="camp-1")
    limits.before("prober", scope)

    limits.after("prober", scope, True, CallUsage(input_tokens=80, output_tokens=20))

    assert reason_of(limits, scope) is LimitReason.CAMPAIGN_CEILING


def test_breaker_opens_per_role_and_recovers() -> None:
    clock = FakeClock()
    limits = build_limits(clock)
    for _ in range(2):
        limits.before("prober", CallScope())
        limits.after("prober", CallScope(), False, None)

    assert reason_of(limits, CallScope()) is LimitReason.BREAKER_OPEN
    limits.before("victim", CallScope())
    clock.now = 31
    limits.before("prober", CallScope())


def test_daily_usd_budget_denies_once_spent() -> None:
    limits = build_limits(FakeClock(), daily_usd=0.01)
    limits.before("victim", CallScope())

    limits.after("victim", CallScope(), True, CallUsage(input_tokens=1), cost_usd=0.01)

    assert reason_of(limits, CallScope()) is LimitReason.DAILY_BUDGET


def test_budget_survives_restarts_through_the_ledger() -> None:
    limits = build_limits(FakeClock(), daily_usd=0.05)
    spent_today = call_record(cost=CallCost(output_usd=0.05)).model_copy(
        update={"origin": CallOrigin.LIVE, "at": datetime(2026, 10, 24, 12, tzinfo=UTC)}
    )
    spent_yesterday = spent_today.model_copy(update={"at": datetime(2026, 10, 23, tzinfo=UTC)})
    simulated = call_record(cost=CallCost(output_usd=9.0))

    limits.charge_history([spent_today, spent_yesterday, simulated])

    assert limits.spent_today_usd() == 0.05
    assert reason_of(limits, CallScope()) is LimitReason.DAILY_BUDGET
