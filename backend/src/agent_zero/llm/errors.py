import anthropic
from strands.types.exceptions import ModelThrottledException

from agent_zero.llm.models import LimitReason

TRANSIENT_ERRORS: tuple[type[BaseException], ...] = (
    TimeoutError,
    ConnectionError,
    ModelThrottledException,
    anthropic.APIConnectionError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
    anthropic.OverloadedError,
    anthropic.ServiceUnavailableError,
    anthropic.DeadlineExceededError,
)


class ModelLimitReachedError(RuntimeError):
    def __init__(self, message: str, reason: LimitReason) -> None:
        super().__init__(message)
        self.reason = reason


class ModelRefusedError(RuntimeError):
    def __init__(self, role: str) -> None:
        super().__init__(f"el modelo del rol {role} declinó la solicitud")
        self.role = role


class StructuredOutputError(RuntimeError):
    def __init__(self, output_model: str, attempts: int, cause: Exception) -> None:
        super().__init__(
            f"{output_model} no validó tras {attempts} intento(s): {type(cause).__name__}: {cause}"
        )
        self.output_model = output_model
        self.attempts = attempts
        self.cause = cause


def transient(error: BaseException) -> bool:
    return isinstance(error, TRANSIENT_ERRORS)
