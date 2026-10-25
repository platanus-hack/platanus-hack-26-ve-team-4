"""Contrato de GET /api/operator/live (v2). Espejo: frontend/src/features/board/types.ts."""

from typing import Any, Literal

from pydantic import BaseModel

SessionKind = Literal["audience", "swarm", "prober"]
Scope = Literal["all", "swarm_prober"]
RouteName = Literal["protected", "honeypot"]


class LiveDenial(BaseModel):
    """Llamada negada por el gateway. Sin argumentos ni detalle: pueden traer datos ajenos."""

    tool: str
    reason: str
    validator: str | None


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
    outcome: str | None
    route: RouteName | None
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
    concealed: bool
    route: RouteName | None
    customer_id: str
    last_activity: str
    attempt_total: int
    contained_n: int | None
    prevented_n: int | None
    leaked_n: int | None
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
