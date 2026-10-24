from collections.abc import Callable
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_zero.config import Settings
from agent_zero.fleet.token_vault import TokenNotFoundError, TokenVault
from agent_zero.identity.credential_verifier import CredentialVerifier
from agent_zero.identity.errors import IdentityDeniedError
from agent_zero.identity.models import IdentityDenialReason
from agent_zero.identity.revocation_service import RevocationService
from agent_zero.identity.schemas import AgentPrincipal
from agent_zero.shared.clock import utc_now


class VaultPrincipalGuard:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        settings: Settings,
        vault: TokenVault,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._sessions = sessions
        self._settings = settings
        self._vault = vault
        self._clock = clock

    async def authorize(self, principal: AgentPrincipal, scope: str) -> AgentPrincipal:
        try:
            token = self._vault.token_for(principal.credential_id)
        except TokenNotFoundError as missing:
            raise IdentityDeniedError(IdentityDenialReason.MALFORMED) from missing
        async with self._sessions() as db:
            verifier = CredentialVerifier(
                self._settings, RevocationService(db, self._clock), self._clock
            )
            verified = await verifier.verify(token, scope)
        if verified != principal:
            raise IdentityDeniedError(IdentityDenialReason.BAD_SIGNATURE)
        return verified
