from datetime import UTC, datetime, timedelta

from agent_zero.config import Settings
from agent_zero.prober.adaptive_planner import AdaptivePlanner, Finish, Hold, RoundStats

NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)


def _planner(settings: Settings, now: datetime = NOW) -> AdaptivePlanner:
    return AdaptivePlanner(settings, lambda: now)


def test_a_full_round_without_a_break_ends_the_campaign_as_held(settings: Settings) -> None:
    decision = _planner(settings)._round_over(RoundStats(queries=8, violations=0, last_update=NOW))

    assert decision == Finish("held_within_budget")


def test_a_full_round_with_a_break_waits_for_the_defense(settings: Settings) -> None:
    stats = RoundStats(queries=8, violations=2, mutator="seed", last_update=NOW)

    assert _planner(settings, NOW + timedelta(seconds=5))._round_over(stats) == Hold()


def test_the_wait_for_the_defense_has_a_deadline(settings: Settings) -> None:
    stats = RoundStats(queries=8, violations=1, mutator="seed", last_update=NOW)
    late = NOW + timedelta(seconds=settings.prober_round_close_wait_seconds + 1)

    assert _planner(settings, late)._round_over(stats) == Finish("defender_did_not_close")


def test_default_budget_is_eight_queries_per_policy_version(settings: Settings) -> None:
    assert settings.prober_round_query_budget == 8
