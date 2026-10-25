"""Contrato de GET /api/operator/live (v3). Espejo: frontend/src/features/board/types.ts."""

from typing import Any, Literal

from pydantic import BaseModel

SessionKind = Literal["audience", "swarm", "prober", "test"]
Scope = Literal["all", "swarm_prober"]  # El servidor solo emite "all" (toda la ronda).
RouteName = Literal["protected", "honeypot"]
# Categoría cerrada del control que negó una herramienta. Sustituye al id del validador:
# el tablero se proyecta al público y no debe llevar ids de validador ni de regla de flujo.
DenialControl = Literal[
    "pedido_ajeno",
    "limite_reembolso",
    "memoria_protegida",
    "origen",
    "regla_flujo",
    "pedido_inexistente",
    "contexto",
    "otro",
]


class LiveDenial(BaseModel):
    """Llamada negada por el gateway. Sin argumentos, detalle ni id de validador o de regla."""

    tool: str
    reason: str
    control: DenialControl | None


class LiveTechnique(BaseModel):
    """Familia y mutador del caso de campaña del Prober; el enjambre no la informa."""

    family: str
    mutator: str | None


class LivePatch(BaseModel):
    version: int
    seconds_after: float


class LiveAttempt(BaseModel):
    id: str
    number: int
    status: str
    outcome: str | None  # None solo mientras el intento no ha terminado.
    route: RouteName
    policy_version: int
    messages: list[str]
    reply: str
    denials: list[LiveDenial]
    violated_objectives: list[str]
    patched_by: LivePatch | None
    technique: LiveTechnique | None
    created_at: str
    updated_at: str


class LiveSession(BaseModel):
    session_id: str
    alias: str
    kind: SessionKind
    route: RouteName
    customer_id: str
    last_activity: str
    attempt_total: int
    contained_n: int
    prevented_n: int
    leaked_n: int
    attempts: list[LiveAttempt]


class AttackKpi(BaseModel):
    n: int
    audience: int
    swarm: int
    prober: int
    in_flight: int
    source: str


class SafeSpaceKpi(BaseModel):
    n: int
    safe_sessions: int
    diverted_sessions: int
    contained_attempts: int
    scope: Scope
    label: str
    source: str


class LeakedKpi(BaseModel):
    n: int
    leaked: int
    by_objective: dict[str, int]
    objective_sum: int
    scope: Scope
    label: str
    source: str


class TokenPart(BaseModel):
    measured: bool
    tokens: int | None
    calls: int


class TokensKpi(BaseModel):
    measured: bool
    label: str
    attacker: TokenPart
    decoy: TokenPart
    n: int
    source: str


class PatchesKpi(BaseModel):
    n: int
    activated: int
    current_version: int
    median_seconds_to_patch: float | None
    findings_covered: int
    findings_total: int
    source: str


class LiveKpis(BaseModel):
    attacks: AttackKpi
    safe_space: SafeSpaceKpi
    leaked: LeakedKpi
    attacker_tokens: TokensKpi
    patches: PatchesKpi


class LiveBoard(BaseModel):
    revealed: bool
    accepting: bool
    llm_mode: str
    policy_version: int
    sessions_total: int
    sessions: list[LiveSession]
    kpis: LiveKpis
    generated_at: str


Row = dict[str, Any]
