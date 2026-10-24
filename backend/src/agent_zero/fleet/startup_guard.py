from agent_zero.config import Settings
from agent_zero.memory_bank.memory_cipher import LOCAL_ENVIRONMENTS

DEFAULT_SECRETS = frozenset({"change-me", "change-me-identity", ""})
MIN_SECRET_LENGTH = 32
SHARED_SECRET = "la clave de firma de identidad y el secreto de operador son iguales"


class InsecureConfigurationError(RuntimeError):
    def __init__(self, problems: tuple[str, ...]) -> None:
        super().__init__(
            "Configuración insegura para un entorno que no es local ni de prueba: "
            + "; ".join(problems)
        )
        self.problems = problems


def _weak(name: str, value: str) -> str | None:
    if value in DEFAULT_SECRETS:
        return f"{name} conserva su valor por defecto o está vacío"
    if len(value) < MIN_SECRET_LENGTH:
        return f"{name} mide menos de {MIN_SECRET_LENGTH} caracteres"
    return None


def enforce_secure_settings(settings: Settings) -> None:
    if settings.environment in LOCAL_ENVIRONMENTS:
        return
    signing = settings.identity_signing_key.get_secret_value()
    operator = settings.operator_secret.get_secret_value()
    found = (
        _weak("AGENT_ZERO_IDENTITY_SIGNING_KEY", signing),
        _weak("AGENT_ZERO_OPERATOR_SECRET", operator),
        SHARED_SECRET if signing == operator else None,
    )
    problems = tuple(problem for problem in found if problem is not None)
    if problems:
        raise InsecureConfigurationError(problems)
