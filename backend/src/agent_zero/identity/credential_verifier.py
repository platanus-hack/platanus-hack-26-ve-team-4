from collections.abc import Callable
from datetime import datetime

from agent_zero.config import Settings
from agent_zero.identity.errors import IdentityDeniedError
from agent_zero.identity.models import IdentityDenialReason
from agent_zero.identity.revocation_service import RevocationService
from agent_zero.identity.schemas import SCOPE_PATTERN, AgentPrincipal
from agent_zero.identity.token_codec import TokenCodec
from agent_zero.shared.clock import utc_now


class CredentialVerifier:
    def __init__(
        self,
        settings: Settings,
        revocations: RevocationService,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._codec = TokenCodec(settings.identity_signing_key.get_secret_value().encode("utf-8"))
        self._revocations = revocations
        self._clock = clock

    async def verify(self, token: str, required_scope: str) -> AgentPrincipal:
        principal = self._codec.decode(token)
        if self._clock() >= principal.expires_at:
            raise IdentityDeniedError(IdentityDenialReason.EXPIRED)
        if await self._revocations.is_revoked(principal):
            raise IdentityDeniedError(IdentityDenialReason.REVOKED)
        if not SCOPE_PATTERN.fullmatch(required_scope) or required_scope not in principal.scopes:
            raise IdentityDeniedError(IdentityDenialReason.MISSING_SCOPE)
        return principal
