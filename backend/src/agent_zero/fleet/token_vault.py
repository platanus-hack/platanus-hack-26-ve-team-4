from collections.abc import Callable
from datetime import datetime

from agent_zero.identity.schemas import IssuedCredential
from agent_zero.shared.clock import utc_now


class TokenNotFoundError(LookupError):
    def __init__(self, credential_id: str) -> None:
        super().__init__(f"No hay una credencial vigente para {credential_id}.")
        self.credential_id = credential_id


class TokenVault:
    def __init__(self, clock: Callable[[], datetime] = utc_now) -> None:
        self._clock = clock
        self._tokens: dict[str, IssuedCredential] = {}

    def put(self, credential: IssuedCredential) -> None:
        self._purge()
        self._tokens[credential.principal.credential_id] = credential

    def token_for(self, credential_id: str) -> str:
        credential = self._tokens.get(credential_id)
        if credential is None:
            raise TokenNotFoundError(credential_id)
        return credential.token

    def size(self) -> int:
        self._purge()
        return len(self._tokens)

    def _purge(self) -> None:
        now = self._clock()
        expired = [key for key, item in self._tokens.items() if item.principal.expires_at <= now]
        for key in expired:
            del self._tokens[key]
