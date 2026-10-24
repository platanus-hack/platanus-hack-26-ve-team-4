from enum import StrEnum


class ModelRole(StrEnum):
    VICTIM = "victim"
    DECOY = "decoy"
    PROBER = "prober"
    ANALYZER = "analyzer"
    PATCHER = "patcher"


class LlmMode(StrEnum):
    LIVE = "live"
    RECORD = "record"
    REPLAY = "replay"
    OFFLINE = "offline"


class CallKind(StrEnum):
    STREAM = "stream"
    STRUCTURED = "structured_output"


class CallOrigin(StrEnum):
    LIVE = "live"
    REPLAYED = "replayed"
    SIMULATED = "simulated"


class CallOutcome(StrEnum):
    OK = "ok"
    FAILED = "failed"
    DENIED = "denied"
    REFUSED = "refused"


class LimitReason(StrEnum):
    BREAKER_OPEN = "breaker_open"
    DAILY_CEILING = "daily_ceiling"
    SESSION_CEILING = "session_ceiling"
    CAMPAIGN_CEILING = "campaign_ceiling"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
