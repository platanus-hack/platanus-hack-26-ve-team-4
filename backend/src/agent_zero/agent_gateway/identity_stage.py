from collections.abc import Callable
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_zero.agent_gateway.errors import GatewayDeniedError
from agent_zero.agent_gateway.models import GatewayReason, GatewayStage
from agent_zero.config import Settings
from agent_zero.identity.credential_verifier import CredentialVerifier
from agent_zero.identity.errors import IdentityDeniedError
from agent_zero.identity.models import IdentityDenialReason
from agent_zero.identity.revocation_service import RevocationService
from agent_zero.identity.schemas import AgentPrincipal

_REASONS = {
    IdentityDenialReason.MALFORMED: GatewayReason.IDENTITY_MALFORMED,
    IdentityDenialReason.BAD_SIGNATURE: GatewayReason.IDENTITY_BAD_SIGNATURE,
    IdentityDenialReason.EXPIRED: GatewayReason.IDENTITY_EXPIRED,
    IdentityDenialReason.REVOKED: GatewayReason.IDENTITY_REVOKED,
    IdentityDenialReason.MISSING_SCOPE: GatewayReason.IDENTITY_MISSING_SCOPE,
}


class IdentityStage:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        settings: Settings,
        clock: Callable[[], datetime],
    ) -> None:
        self._sessions = sessions
        self._settings = settings
        self._clock = clock

    async def authenticate(self, token: str, scope: str) -> AgentPrincipal:
        async with self._sessions() as db:
            verifier = CredentialVerifier(
                self._settings, RevocationService(db, self._clock), self._clock
            )
            try:
                return await verifier.verify(token, scope)
            except IdentityDeniedError as denial:
                raise GatewayDeniedError(_REASONS[denial.reason], GatewayStage.IDENTITY) from denial
