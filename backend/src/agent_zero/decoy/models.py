from pydantic import BaseModel

MIN_RATE_N = 5


class SessionTrace(BaseModel):
    session_id: str
    alias: str
    reason: str
    retained_seconds: float
    post_diversion_steps: int
    post_diversion_attempts: int
    honeytools_touched: list[str]
    credential_issued: bool
    token_reused: bool
    retained: bool
    bait_taken: bool
    deceived: bool


class Rate(BaseModel):
    k: int
    n: int
    value: float | None


class DecoySummary(BaseModel):
    diverted_n: int
    excluded_autonomous_n: int
    small_n: bool
    retained: Rate
    bait_taken: Rate
    deceived: Rate
    median_retained_seconds: float | None
    cases: list[SessionTrace]


class RevealCard(BaseModel):
    retained_seconds: float
    post_diversion_steps: int
    post_diversion_attempts: int
    honeytools_touched: list[str]
    credential_issued: bool
    token_reused: bool
