from typing import Any, Literal

from pydantic import BaseModel

SessionKind = Literal["audience", "swarm", "prober"]
Scope = Literal["all", "swarm_prober"]


class LiveAttempt(BaseModel):
    id: str
    status: str
    outcome: str | None
    route: str | None
    messages: list[str]
    reply: str
    created_at: str


class LiveSession(BaseModel):
    session_id: str
    alias: str
    kind: SessionKind
    route: str | None
    customer_id: str
    last_activity: str
    attempt_total: int
    attempts: list[LiveAttempt]


class AttackKpi(BaseModel):
    n: int
    audience: int
    swarm: int
    prober: int
    source: str


class SafeSpaceKpi(BaseModel):
    n: int
    diverted_sessions: int
    contained_attempts: int
    scope: Scope
    label: str
    source: str


class LeakedKpi(BaseModel):
    n: int
    leaked: int
    by_objective: dict[str, int]
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
    source: str


class LiveKpis(BaseModel):
    attacks: AttackKpi
    safe_space: SafeSpaceKpi
    leaked: LeakedKpi
    attacker_tokens: TokensKpi
    patches: PatchesKpi


class LiveBoard(BaseModel):
    revealed: bool
    llm_mode: str
    policy_version: int
    sessions: list[LiveSession]
    kpis: LiveKpis
    generated_at: str


Row = dict[str, Any]
