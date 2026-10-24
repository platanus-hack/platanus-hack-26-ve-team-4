import time
from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime

from pydantic import Field

from agent_zero.config import Settings
from agent_zero.llm.breaker import CircuitBreaker
from agent_zero.llm.errors import ModelLimitReachedError
from agent_zero.llm.models import CallOrigin, LimitReason
from agent_zero.llm.quota import CallQuota, Reservation
from agent_zero.llm.schemas import CallRecord, CallScope, CallUsage, FrozenModel


class LimitPolicy(FrozenModel):
    daily_calls: int = Field(ge=1)
    session_calls: int = Field(ge=1)
    campaign_calls: int = Field(ge=1)
    campaign_tokens: int = Field(ge=1)
    daily_usd: float = Field(gt=0)
    breaker_failures: int = Field(ge=1)
    breaker_recovery_seconds: float = Field(gt=0)

    @classmethod
    def from_settings(cls, settings: Settings) -> "LimitPolicy":
        return cls(
            daily_calls=settings.llm_daily_call_limit,
            session_calls=settings.llm_session_call_limit,
            campaign_calls=settings.llm_campaign_call_limit,
            campaign_tokens=settings.llm_campaign_token_limit,
            daily_usd=settings.llm_daily_usd_limit,
            breaker_failures=settings.llm_breaker_failures,
            breaker_recovery_seconds=settings.llm_breaker_recovery_seconds,
        )


def _utc_today() -> date:
    return datetime.now(UTC).date()


class ModelLimits:
    def __init__(
        self,
        policy: LimitPolicy,
        quota: CallQuota,
        monotonic: Callable[[], float] = time.monotonic,
        today: Callable[[], date] = _utc_today,
    ) -> None:
        self.policy = policy
        self.quota = quota
        self._monotonic = monotonic
        self._today = today
        self._breakers: dict[str, CircuitBreaker] = {}
        self._spent_usd: defaultdict[date, float] = defaultdict(float)

    def breaker(self, role: str) -> CircuitBreaker:
        return self._breakers.setdefault(
            role,
            CircuitBreaker(self.policy.breaker_failures, self.policy.breaker_recovery_seconds),
        )

    def spent_today_usd(self) -> float:
        return self._spent_usd[self._today()]

    def charge_history(self, records: Iterable[CallRecord]) -> None:
        for record in records:
            if record.origin is CallOrigin.LIVE and record.cost is not None:
                self._spent_usd[record.at.astimezone(UTC).date()] += record.cost.total_usd

    def before(self, role: str, scope: CallScope) -> None:
        if self.spent_today_usd() >= self.policy.daily_usd:
            raise ModelLimitReachedError(
                f"se agotó el presupuesto diario de US$ {self.policy.daily_usd:.2f}",
                LimitReason.DAILY_BUDGET,
            )
        if not self.breaker(role).allow(self._monotonic()):
            raise ModelLimitReachedError(
                f"el proveedor del rol {role} está en pausa por fallos recientes",
                LimitReason.BREAKER_OPEN,
            )
        campaign = f"campaign:{scope.campaign_id}" if scope.campaign_id else None
        if campaign and self.quota.tokens(campaign) >= self.policy.campaign_tokens:
            raise ModelLimitReachedError(
                "la campaña agotó su presupuesto de tokens", LimitReason.CAMPAIGN_CEILING
            )
        reservations, reasons = self._reservations(scope, campaign)
        exceeded = self.quota.reserve(reservations)
        if exceeded is not None:
            raise ModelLimitReachedError(f"se alcanzó el tope de {exceeded}", reasons[exceeded])

    def after(
        self,
        role: str,
        scope: CallScope,
        success: bool,
        usage: CallUsage | None,
        cost_usd: float = 0.0,
    ) -> None:
        self._spent_usd[self._today()] += cost_usd
        breaker = self.breaker(role)
        if success:
            breaker.record_success()
        else:
            breaker.record_failure(self._monotonic())
        if scope.campaign_id and usage is not None:
            self.quota.add_tokens(f"campaign:{scope.campaign_id}", usage.total_tokens)

    def _reservations(
        self, scope: CallScope, campaign: str | None
    ) -> tuple[list[Reservation], dict[str, LimitReason]]:
        day = f"day:{self._today().isoformat()}"
        reservations: list[Reservation] = [(day, self.policy.daily_calls)]
        reasons = {day: LimitReason.DAILY_CEILING}
        if scope.session_id:
            session = f"session:{scope.session_id}"
            reservations.append((session, self.policy.session_calls))
            reasons[session] = LimitReason.SESSION_CEILING
        if campaign:
            reservations.append((campaign, self.policy.campaign_calls))
            reasons[campaign] = LimitReason.CAMPAIGN_CEILING
        return reservations, reasons
