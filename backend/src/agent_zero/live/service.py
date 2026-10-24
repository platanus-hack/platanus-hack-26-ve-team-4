from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from statistics import median
from typing import Any

from sqlalchemy import select

from agent_zero.arena.core import ProductCore
from agent_zero.attempts.attempt_query_service import attempt_view
from agent_zero.attempts.models import Attempt, AttemptOutcome
from agent_zero.live.models import (
    AttackKpi,
    LeakedKpi,
    LiveAttempt,
    LiveBoard,
    LiveKpis,
    LiveSession,
    PatchesKpi,
    SafeSpaceKpi,
    Scope,
    SessionKind,
    TokenPart,
    TokensKpi,
)
from agent_zero.llm.gateway import LlmGateway
from agent_zero.llm.reporting import measured_tokens
from agent_zero.llm.schemas import CallRecord
from agent_zero.routing.models import Route
from agent_zero.sessions.models import ArenaSession
from agent_zero.shared.clock import utc_now

PROBER_ALIAS = "Prober"
SWARM_PREFIX = "Agente-"
MAX_ATTEMPTS_PER_SESSION = 30
SCOPE_LABELS: dict[Scope, str] = {
    "all": "Toda la ronda",
    "swarm_prober": "Solo enjambre y Prober hasta revelar",
}
NOT_MEASURED_DEMO = "no medido en modo demo"
NOT_MEASURED = "sin uso de tokens registrado"


def session_kind(session: ArenaSession) -> SessionKind | None:
    """Clasifica una sesión; `None` excluye las repeticiones del operador."""
    if session.id.startswith("internal-"):
        return "prober" if session.alias == PROBER_ALIAS else None
    return "swarm" if session.alias.startswith(SWARM_PREFIX) else "audience"


def _concealed(kind: SessionKind, revealed: bool) -> bool:
    return kind == "audience" and not revealed


def _live_attempt(attempt: Attempt, kind: SessionKind, revealed: bool) -> LiveAttempt:
    concealed = _concealed(kind, revealed)
    # `attempt_view` ya redacta referencias y aplica la regla pública de resultado aparente.
    view = attempt_view(attempt, operator=not concealed, revealed=revealed)
    return LiveAttempt(
        id=view["id"],
        status=view["status"],
        outcome=view["outcome"],
        route=None if concealed else attempt.route.value,
        messages=list(view["messages"]),
        reply=view["reply"],
        created_at=view["created_at"],
    )


def _violated_objectives(attempt: Attempt) -> list[str]:
    verdicts = (attempt.assessment or {}).get("verdicts", [])
    return [str(v["objective_id"]) for v in verdicts if v.get("violated")]


def _token_part(records: list[CallRecord]) -> TokenPart:
    measured = measured_tokens(records)
    return TokenPart(
        measured=measured is not None,
        tokens=None if measured is None else measured[0],
        calls=0 if measured is None else measured[1],
    )


def _tokens_kpi(
    records: Iterable[CallRecord], campaigns: set[str], sessions: set[str], llm_mode: str
) -> TokensKpi:
    ledger = list(records)
    attacker = _token_part(
        [r for r in ledger if r.role == "prober" and r.scope.campaign_id in campaigns]
    )
    decoy = _token_part([r for r in ledger if r.role == "decoy" and r.scope.session_id in sessions])
    measured = attacker.measured or decoy.measured
    return TokensKpi(
        measured=measured,
        label="" if measured else (NOT_MEASURED_DEMO if llm_mode == "demo" else NOT_MEASURED),
        attacker=attacker,
        decoy=decoy,
        n=attacker.calls + decoy.calls,
        source="Ledger de llamadas LLM: rol prober por campaña, rol decoy por sesión.",
    )


def _patches_kpi(policies: list[dict[str, Any]], findings: list[dict[str, Any]]) -> PatchesKpi:
    created = {f["id"]: datetime.fromisoformat(f["created_at"]) for f in findings}
    activated = [p for p in policies if p["version"] > 0 and p["activated_at"]]
    seconds: list[float] = []
    for policy in activated:
        at = datetime.fromisoformat(policy["activated_at"])
        seconds.extend(
            max(0.0, (at - created[finding_id]).total_seconds())
            for finding_id in policy["finding_ids"]
            if finding_id in created
        )
    current = next((p["version"] for p in policies if p["status"] == "active"), 0)
    return PatchesKpi(
        n=len(activated),
        activated=len(activated),
        current_version=current,
        median_seconds_to_patch=round(median(seconds), 3) if seconds else None,
        findings_covered=len(seconds),
        source="Versiones de política activadas sobre la base y hallazgos que cubren.",
    )


@dataclass(frozen=True)
class BoardData:
    attempts: list[Attempt]
    sessions: list[ArenaSession]
    policies: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    records: Iterable[CallRecord]


def build_board(
    data: BoardData, *, revealed: bool, llm_mode: str, limit: int, now: datetime | None = None
) -> LiveBoard:
    attempts, sessions = data.attempts, data.sessions
    kinds = {s.id: k for s in sessions if (k := session_kind(s)) is not None}
    by_id = {s.id: s for s in sessions}
    by_session: dict[str, list[Attempt]] = defaultdict(list)
    for attempt in attempts:
        if attempt.session_id in kinds:
            by_session[attempt.session_id].append(attempt)

    def activity(session_id: str) -> datetime:
        return max(a.updated_at for a in by_session[session_id])

    recent = sorted(by_session, key=activity, reverse=True)[:limit]
    live_sessions = [
        LiveSession(
            session_id=sid,
            alias=by_id[sid].alias,
            kind=kinds[sid],
            route=None if _concealed(kinds[sid], revealed) else by_id[sid].route.value,
            customer_id=by_id[sid].customer_id,
            last_activity=activity(sid).isoformat(),
            attempt_total=len(by_session[sid]),
            attempts=[
                _live_attempt(a, kinds[sid], revealed)
                for a in by_session[sid][-MAX_ATTEMPTS_PER_SESSION:]
            ],
        )
        for sid in recent
    ]

    scope: Scope = "all" if revealed else "swarm_prober"
    in_scope = {sid for sid, kind in kinds.items() if revealed or kind != "audience"}
    scoped = [a for a in attempts if a.session_id in in_scope]
    counts = Counter(kinds[a.session_id] for a in attempts if a.session_id in kinds)
    leaked = [a for a in scoped if a.outcome is AttemptOutcome.CONFIRMED_VIOLATION]
    campaigns = {a.campaign_id for a in attempts if a.campaign_id and a.session_id in kinds}

    kpis = LiveKpis(
        attacks=AttackKpi(
            n=sum(counts.values()),
            audience=counts["audience"],
            swarm=counts["swarm"],
            prober=counts["prober"],
            source="Intentos de la ronda; excluye repeticiones del operador.",
        ),
        safe_space=SafeSpaceKpi(
            n=len(in_scope),
            diverted_sessions=sum(by_id[sid].route is Route.HONEYPOT for sid in in_scope),
            contained_attempts=sum(a.outcome is AttemptOutcome.CONTAINED_HONEYPOT for a in scoped),
            scope=scope,
            label=SCOPE_LABELS[scope],
            source="Sesiones con ruta honeypot sobre las sesiones con alcance.",
        ),
        leaked=LeakedKpi(
            n=len(scoped),
            leaked=len(leaked),
            by_objective=dict(Counter(o for a in leaked for o in _violated_objectives(a))),
            scope=scope,
            label=SCOPE_LABELS[scope],
            source="Intentos confirmed_violation sobre los intentos con alcance.",
        ),
        attacker_tokens=_tokens_kpi(data.records, campaigns, in_scope, llm_mode),
        patches=_patches_kpi(data.policies, data.findings),
    )
    return LiveBoard(
        revealed=revealed,
        llm_mode=llm_mode,
        policy_version=kpis.patches.current_version,
        sessions=live_sessions,
        kpis=kpis,
        generated_at=(now or utc_now()).isoformat(),
    )


class LiveBoardService:
    def __init__(self, core: ProductCore, llm: LlmGateway) -> None:
        self._core = core
        self._llm = llm

    async def board(self, limit: int) -> LiveBoard:
        core = self._core
        async with core.fleet.database.sessions() as db:
            sessions = list(await db.scalars(select(ArenaSession)))
        data = BoardData(
            attempts=await core.attempts.all(),
            sessions=sessions,
            policies=await core.policies.all(),
            findings=await core.findings.all(),
            records=self._llm.ledger.records(),
        )
        return build_board(
            data,
            revealed=await core.attempts.revealed(),
            llm_mode=self._llm.mode.value,
            limit=limit,
        )
