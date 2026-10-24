class AttemptRejectedError(Exception):
    """Un intento que no se acepta; `retry_after` en segundos cuando tiene sentido reintentar."""

    def __init__(self, detail: str, retry_after: int | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.retry_after = retry_after


class TooFrequentError(AttemptRejectedError):
    pass


class QueueFullError(AttemptRejectedError):
    pass


class TargetUnavailableError(AttemptRejectedError):
    pass
