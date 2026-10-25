import base64

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from agent_zero.config import Settings
from agent_zero.memory_bank.errors import MemoryConfigError

LOCAL_ENVIRONMENTS = frozenset({"local", "test"})
HKDF_INFO = b"agent-zero-memory"
MIN_DERIVED_SECRET = 32


def _is_fernet_key(value: str) -> bool:
    try:
        return len(base64.urlsafe_b64decode(value.encode("ascii"))) == 32 and len(value) == 44
    except (ValueError, UnicodeEncodeError):
        return False


def _derive(secret: str) -> bytes:
    derived = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=HKDF_INFO).derive(
        secret.encode("utf-8")
    )
    return base64.urlsafe_b64encode(derived)


class MemoryCipher:
    def __init__(self, key: bytes) -> None:
        try:
            self._fernet = Fernet(key)
        except ValueError as error:
            raise MemoryConfigError(
                "La clave de cifrado de memoria no es una clave Fernet válida."
            ) from error

    @classmethod
    def from_settings(cls, settings: Settings) -> "MemoryCipher":
        configured = settings.memory_encryption_key.get_secret_value()
        if configured:
            if _is_fernet_key(configured):
                return cls(configured.encode("utf-8"))
            if len(configured) < MIN_DERIVED_SECRET:
                raise MemoryConfigError(
                    "La clave de cifrado de memoria no es una clave Fernet válida."
                )
            return cls(_derive(configured))
        if settings.environment not in LOCAL_ENVIRONMENTS:
            raise MemoryConfigError(
                "Falta AGENT_ZERO_MEMORY_ENCRYPTION_KEY: la memoria no puede "
                "cifrarse en un entorno distinto de local o test."
            )
        return cls(_derive(settings.operator_secret.get_secret_value()))

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")
        except InvalidToken as error:
            raise MemoryConfigError(
                "No se pudo descifrar un recuerdo: la clave de memoria cambió."
            ) from error
