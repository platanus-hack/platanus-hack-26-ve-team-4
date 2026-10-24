from collections.abc import Callable
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_zero.fleet.token_vault import TokenVault
from agent_zero.identity.credential_issuer import CredentialIssuer
from agent_zero.identity.revocation_service import RevocationService
from agent_zero.identity.schemas import AgentPrincipal
from agent_zero.registry.errors import RegistryError
from agent_zero.registry.grant_service import grant_for
from agent_zero.runtime.admission import AdmissionDeniedError
from agent_zero.shared.clock import utc_now


class RegistryAdmission:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        issuer: CredentialIssuer,
        vault: TokenVault,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._sessions = sessions
        self._issuer = issuer
        self._vault = vault
        self._clock = clock

    async def admit(self, agent_id: str, version: str) -> AgentPrincipal:
        async with self._sessions() as db:
            try:
                grant = await grant_for(db, agent_id, version)
            except RegistryError as error:
                raise AdmissionDeniedError(str(error)) from error
            credential = self._issuer.issue(grant)
            if await RevocationService(db, self._clock).is_revoked(credential.principal):
                raise AdmissionDeniedError(
                    f"el agente {agent_id} {version} tiene la identidad revocada."
                )
        self._vault.put(credential)
        return credential.principal
