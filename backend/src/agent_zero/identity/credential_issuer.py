from collections.abc import Callable
from datetime import datetime, timedelta

from agent_zero.config import Settings
from agent_zero.identity.schemas import AgentGrant, AgentPrincipal, IssuedCredential
from agent_zero.identity.token_codec import TokenCodec
from agent_zero.shared.clock import utc_now
from agent_zero.shared.ids import new_id


class CredentialIssuer:
    def __init__(self, settings: Settings, clock: Callable[[], datetime] = utc_now) -> None:
        self._codec = TokenCodec(settings.identity_signing_key.get_secret_value().encode("utf-8"))
        self._ttl = timedelta(seconds=settings.identity_token_ttl_seconds)
        self._clock = clock

    def issue(self, grant: AgentGrant) -> IssuedCredential:
        issued_at = self._clock()
        principal = AgentPrincipal(
            credential_id=new_id("cred"),
            agent_id=grant.agent_id,
            version=grant.version,
            department=grant.department,
            scopes=grant.scopes,
            clearance=grant.clearance,
            allowed_regions=grant.allowed_regions,
            issued_at=issued_at,
            expires_at=issued_at + self._ttl,
        )
        return IssuedCredential(token=self._codec.encode(principal), principal=principal)
