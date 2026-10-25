from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from statistics import median
from typing import Any

from sqlalchemy import select

from agent_zero.arena.core import ProductCore
from agent_zero.arena.models import ArenaState
from agent_zero.attempts.attempt_query_service import attempt_view
from agent_zero.attempts.models import Attempt, AttemptOutcome, AttemptStatus
from agent_zero.events.models import EventRecord, EventType, Visibility
from agent_zero.live.models import (
    AttackKpi,
    DenialControl,
    LeakedKpi,
    LiveAttempt,
    LiveBoard,
    LiveDenial,
    LiveKpis,
    LivePatch,
    LiveSession,
    LiveTechnique,
    PatchesKpi,
    RouteName,
    SafeSpaceKpi,
    Scope,
    SessionKind,
    TokenPart,
    TokensKpi,
)
from agent_zero.live.redaction import redact_live
from agent_zero.llm.gateway import LlmGateway
from agent_zero.llm.reporting import measured_tokens
from agent_zero.llm.schemas import CallRecord
from agent_zero.policies.validator_catalog import OBJECTIVE_CONTROLS
from agent_zero.prober.campaign_models import CampaignCaseRecord
from agent_zero.routing.models import Route
from agent_zero.sessions.models import ArenaSession
from agent_zero.sessions.reserved_alias import SWARM_PREFIX, TEST_PREFIX, counts_in_analytics
from agent_zero.shared.clock import utc_now

PROBER_ALIAS = "Prober"
MAX_ATTEMPTS_PER_SESSION = 30
TERMINAL = {AttemptStatus.EVALUATED, AttemptStatus.INCONCLUSIVE}
SCOPE_LABELS: dict[Scope, str] = {"all": "Toda la ronda"}
NOT_MEASURED_DEMO = "no medido en modo demo"
NOT_MEASURED = "sin uso de tokens registrado"


def session_kind(session: ArenaSession) -> SessionKind | None:
    """Clasifica una sesión; `None` excluye las repeticiones del operador."""
    if session.id.startswith("internal-"):
        return "prober" if session.alias == PROBER_ALIAS else None
    # El servidor reserva el prefijo (`sessions/reserved_alias.py`): el público no puede usarlo.
    if session.alias.startswith(TEST_PREFIX):
        # Chat interno del equipo: se muestra sin enmascarar y no cuenta en las analíticas.
        return "test"
    return "swarm" if session.alias.startswith(SWARM_PREFIX) else "audience"


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _parse(value: str) -> datetime:
    return _aware(datetime.fromisoformat(value))


@dataclass
class BoardGroup:
    """Una "sesión" del tablero: una sesión real, o una campaña completa del Prober."""

    key: str
    kind: SessionKind
    alias: str
    sessions: list[ArenaSession] = field(default_factory=list)
    attempts: list[Attempt] = field(default_factory=list)

    @property
    def activity(self) -> datetime:
        return max(_aware(a.updated_at) for a in self.attempts)

    @property
    def route(self) -> Route:
        honeypot = any(s.route is Route.HONEYPOT for s in self.sessions)
        return Route.HONEYPOT if honeypot else Route.PROTECTED

    @property
    def finished(self) -> list[Attempt]:
        return [a for a in self.attempts if a.status in TERMINAL]

    def sent(self) -> list[tuple[int, Attempt]]:
        numbered = list(enumerate(self.attempts, start=1))
        return numbered[-MAX_ATTEMPTS_PER_SESSION:]


def board_groups(attempts: Iterable[Attempt], sessions: Iterable[ArenaSession]) -> list[BoardGroup]:
    """Agrupa los intentos por sesión del tablero, de la más reciente a la más antigua.

    Cada caso del Prober abre su propia sesión interna; se agrupan por `campaign_id`.
    Solo cuentan las sesiones con al menos un intento; las repeticiones quedan fuera.
    """
    by_id = {s.id: s for s in sessions}
    groups: dict[str, BoardGroup] = {}
    ordered = sorted(attempts, key=lambda a: (_aware(a.created_at), a.id))
    for attempt in ordered:
        session = by_id.get(attempt.session_id)
        kind = session_kind(session) if session else None
        if session is None or kind is None:
            continue
        key = attempt.campaign_id if kind == "prober" and attempt.campaign_id else session.id
        group = groups.get(key)
        if group is None:
            alias = f"{PROBER_ALIAS} · {key[-4:]}" if kind == "prober" else session.alias
            group = groups[key] = BoardGroup(key, kind, alias)
        if session not in group.sessions:
            group.sessions.append(session)
        group.attempts.append(attempt)
    return sorted(groups.values(), key=lambda g: g.activity, reverse=True)


def _violated_objectives(attempt: Attempt) -> list[str]:
    verdicts = (attempt.assessment or {}).get("verdicts", [])
    return [str(v["objective_id"]) for v in verdicts if v.get("violated")]


def _effective_policies(policies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Versiones que llegaron a regir: activadas sobre la base y no revertidas."""
    return [
        p
        for p in policies
        if p["version"] > 0 and p.get("activated_at") and p.get("status") != "rolled_back"
    ]


@dataclass(frozen=True)
class PatchIndex:
    """Para cada intento, las activaciones (versión, momento) de las políticas que lo cubren."""

    by_attempt: Mapping[str, list[tuple[int, datetime]]]

    @classmethod
    def build(cls, findings: list[dict[str, Any]], policies: list[dict[str, Any]]) -> "PatchIndex":
        by_finding: dict[str, list[tuple[int, datetime]]] = defaultdict(list)
        for policy in _effective_policies(policies):
            at = _parse(policy["activated_at"])
            for finding_id in policy.get("finding_ids", []):
                by_finding[finding_id].append((policy["version"], at))
        by_attempt: dict[str, list[tuple[int, datetime]]] = defaultdict(list)
        for finding in findings:
            for attempt_id in finding.get("attempt_ids", []):
                by_attempt[attempt_id].extend(by_finding.get(finding["id"], []))
        return cls(by_attempt)

    def patched_by(self, attempt: Attempt) -> LivePatch | None:
        """El primer parche posterior a la violación que rige sobre una versión más nueva.

        Un hallazgo reabierto acumula intentos posteriores al parche: esos no quedan "parcheados".
        """
        if attempt.outcome is not AttemptOutcome.CONFIRMED_VIOLATION:
            return None
        closed = _aware(attempt.updated_at)
        candidates = [
            (at, version)
            for version, at in self.by_attempt.get(attempt.id, [])
            if version > attempt.policy_version and at >= closed
        ]
        if not candidates:
            return None
        at, version = min(candidates)
        return LivePatch(version=version, seconds_after=round((at - closed).total_seconds(), 3))


@dataclass(frozen=True)
class BoardData:
    attempts: list[Attempt]
    sessions: list[ArenaSession]
    policies: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    records: Iterable[CallRecord]
    denials: Mapping[str, list[LiveDenial]] = field(default_factory=dict)
    techniques: Mapping[str, LiveTechnique] = field(default_factory=dict)


def _live_attempt(
    number: int, attempt: Attempt, data: BoardData, patches: PatchIndex
) -> LiveAttempt:
    view = attempt_view(attempt, operator=True)
    route: RouteName = "honeypot" if attempt.route is Route.HONEYPOT else "protected"
    return LiveAttempt(
        id=attempt.id,
        number=number,
        status=attempt.status.value,
        outcome=view["outcome"],
        route=route,
        policy_version=attempt.policy_version,
        messages=[redact_live(m) for m in attempt.messages],
        reply=redact_live(view["reply"]),
        denials=list(data.denials.get(attempt.id, [])),
        violated_objectives=_violated_objectives(attempt),
        patched_by=patches.patched_by(attempt),
        technique=data.techniques.get(attempt.id),
        created_at=_aware(attempt.created_at).isoformat(),
        updated_at=_aware(attempt.updated_at).isoformat(),
    )


def _count(attempts: Iterable[Attempt], outcome: AttemptOutcome) -> int:
    return sum(a.outcome is outcome for a in attempts)


def _live_session(group: BoardGroup, data: BoardData, patches: PatchIndex) -> LiveSession:
    finished = group.finished
    route: RouteName = "honeypot" if group.route is Route.HONEYPOT else "protected"
    return LiveSession(
        session_id=group.key,
        alias=group.alias,
        kind=group.kind,
        route=route,
        customer_id=group.attempts[-1].customer_id,
        last_activity=group.activity.isoformat(),
        attempt_total=len(group.attempts),
        contained_n=_count(finished, AttemptOutcome.CONTAINED_HONEYPOT),
        prevented_n=_count(finished, AttemptOutcome.PREVENTED),
        leaked_n=_count(finished, AttemptOutcome.CONFIRMED_VIOLATION),
        attempts=[_live_attempt(n, a, data, patches) for n, a in group.sent()],
    )


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


def _patches_kpi(
    policies: list[dict[str, Any]], findings: list[dict[str, Any]], scoped: set[str]
) -> PatchesKpi:
    """Parches sobre los hallazgos con alcance: incluye los intentos del Público en vivo."""
    visible = [f for f in findings if scoped.intersection(f.get("attempt_ids", []))]
    effective = _effective_policies(policies)
    seconds: list[float] = []
    covering: set[int] = set()
    for finding in visible:
        activations = [
            (_parse(p["activated_at"]), p["version"])
            for p in effective
            if finding["id"] in p.get("finding_ids", [])
        ]
        if not activations:
            continue
        at, version = min(activations)
        covering.add(version)
        seconds.append(max(0.0, (at - _parse(finding["created_at"])).total_seconds()))
    current = next((p["version"] for p in policies if p["status"] == "active"), 0)
    return PatchesKpi(
        n=len(covering),
        activated=len(covering),
        current_version=current,
        median_seconds_to_patch=round(median(seconds), 3) if seconds else None,
        findings_covered=len(seconds),
        findings_total=len(visible),
        source="Versiones de política activadas (sin revertir) que cubren hallazgos con alcance; "
        "mediana desde la creación del hallazgo.",
    )


def build_board(  # noqa: PLR0913
    data: BoardData,
    *,
    revealed: bool,
    llm_mode: str,
    limit: int,
    accepting: bool = True,
    now: datetime | None = None,
) -> LiveBoard:
    groups = board_groups(data.attempts, data.sessions)
    patches = PatchIndex.build(data.findings, data.policies)
    live_sessions = [_live_session(g, data, patches) for g in groups[:limit]]

    # Los chats de prueba se muestran pero no mueven las analíticas, salvo los automáticos.
    counted = [g for g in groups if g.kind != "test" or counts_in_analytics(g.alias)]
    scope: Scope = "all"
    finished = [a for g in counted for a in g.finished]
    counts = Counter("swarm" if g.kind == "test" else g.kind for g in counted for _ in g.finished)
    leaked = [a for a in finished if a.outcome is AttemptOutcome.CONFIRMED_VIOLATION]
    by_objective = dict.fromkeys(OBJECTIVE_CONTROLS, 0)
    for objective in (o for a in leaked for o in _violated_objectives(a)):
        by_objective[objective] = by_objective.get(objective, 0) + 1
    diverted = [g for g in counted if g.route is Route.HONEYPOT]
    campaigns = {
        a.campaign_id for g in counted if g.kind == "prober" for a in g.attempts if a.campaign_id
    }
    decoy_sessions = {s.id for g in counted for s in g.sessions}
    scoped_ids = {a.id for g in counted for a in g.attempts}

    kpis = LiveKpis(
        attacks=AttackKpi(
            n=len(finished),
            audience=counts["audience"],
            swarm=counts["swarm"],
            prober=counts["prober"],
            in_flight=sum(len(g.attempts) - len(g.finished) for g in counted),
            source="Intentos terminados de la ronda; excluye repeticiones del operador.",
        ),
        safe_space=SafeSpaceKpi(
            n=len(counted),
            safe_sessions=sum(
                any(a.outcome is AttemptOutcome.CONTAINED_HONEYPOT for a in g.finished)
                for g in diverted
            ),
            diverted_sessions=len(diverted),
            contained_attempts=_count(finished, AttemptOutcome.CONTAINED_HONEYPOT),
            scope=scope,
            label=SCOPE_LABELS[scope],
            source="Sesiones en ruta señuelo con al menos un intento contenido, sobre las "
            "sesiones de la ronda (incluye el Público).",
        ),
        leaked=LeakedKpi(
            n=len(finished),
            leaked=len(leaked),
            by_objective=by_objective,
            objective_sum=sum(by_objective.values()),
            scope=scope,
            label=SCOPE_LABELS[scope],
            source="Intentos confirmed_violation sobre los intentos terminados de la ronda.",
        ),
        attacker_tokens=_tokens_kpi(data.records, campaigns, decoy_sessions, llm_mode),
        patches=_patches_kpi(data.policies, data.findings, scoped_ids),
    )
    return LiveBoard(
        revealed=revealed,
        accepting=accepting,
        llm_mode=llm_mode,
        policy_version=kpis.patches.current_version,
        sessions_total=len(counted),
        sessions=live_sessions,
        kpis=kpis,
        generated_at=(now or utc_now()).isoformat(),
    )


CONTROL_BY_VALIDATOR: dict[str, DenialControl] = {
    "order_belongs_to_session_customer": "pedido_ajeno",
    "refund_within_limit": "limite_reembolso",
    "memory_key_allowlist": "memoria_protegida",
    "require_provenance": "origen",
    "order_exists": "pedido_inexistente",
    "valid_call_context": "contexto",
}


def denial_control(validator: object) -> DenialControl | None:
    """Traduce el validador a una categoría cerrada; el id nunca sale del servidor."""
    if not isinstance(validator, str):
        return None
    if validator.startswith("flow:"):
        return "regla_flujo"
    return CONTROL_BY_VALIDATOR.get(validator, "otro")


def _denial(data: dict[str, Any]) -> LiveDenial:
    return LiveDenial(
        tool=str(data.get("tool", "")),
        reason=str(data.get("reason", "")),
        control=denial_control(data.get("validator")),
    )


def _technique(case: dict[str, Any]) -> LiveTechnique | None:
    family = case.get("family")
    if not isinstance(family, str):
        return None
    mutator = case.get("mutator")
    return LiveTechnique(family=family, mutator=mutator if isinstance(mutator, str) else None)


class LiveBoardService:
    def __init__(self, core: ProductCore, llm: LlmGateway) -> None:
        self._core = core
        self._llm = llm

    async def board(self, limit: int) -> LiveBoard:
        core = self._core
        revealed = await core.attempts.revealed()
        attempts = await core.attempts.all()
        async with core.fleet.database.sessions() as db:
            sessions = list(await db.scalars(select(ArenaSession)))
            state = await db.get(ArenaState, 1)
            groups = board_groups(attempts, sessions)[:limit]
            visible = [a.id for g in groups for _, a in g.sent()]
            probed = [a.id for g in groups if g.kind == "prober" for _, a in g.sent()]
            denials: dict[str, list[LiveDenial]] = defaultdict(list)
            if visible:
                rows = await db.scalars(
                    select(EventRecord)
                    .where(
                        EventRecord.type == EventType.TOOL_DENIED,
                        EventRecord.visibility == Visibility.OPERATOR,
                        EventRecord.attempt_id.in_(visible),
                    )
                    .order_by(EventRecord.id)
                )
                for row in rows:
                    if row.attempt_id:
                        denials[row.attempt_id].append(_denial(row.data))
            techniques: dict[str, LiveTechnique] = {}
            if probed:
                cases = await db.scalars(
                    select(CampaignCaseRecord).where(CampaignCaseRecord.attempt_id.in_(probed))
                )
                for case in cases:
                    technique = _technique(case.case_json)
                    if case.attempt_id and technique:
                        techniques[case.attempt_id] = technique
        data = BoardData(
            attempts=attempts,
            sessions=sessions,
            policies=await core.policies.all(),
            findings=await core.findings.all(),
            records=self._llm.ledger.records(),
            denials=denials,
            techniques=techniques,
        )
        return build_board(
            data,
            revealed=revealed,
            llm_mode=self._llm.mode.value,
            limit=limit,
            accepting=state.accepting if state is not None else True,
        )
