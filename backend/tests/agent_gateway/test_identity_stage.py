import pytest

from agent_zero.agent_gateway.errors import GatewayDeniedError
from agent_zero.agent_gateway.identity_stage import IdentityStage
from agent_zero.agent_gateway.models import GatewayReason, GatewayStage
from agent_zero.config import Settings
from agent_zero.identity.credential_issuer import CredentialIssuer
from agent_zero.identity.revocation_service import RevocationService
from agent_zero.identity.schemas import AgentGrant
from agent_zero.shared.classification import DataClassification
from agent_zero.shared.database import Database
from tests.identity.conftest import FakeClock


@pytest.mark.requirement("IDN-02", "IDN-03")
async def test_maps_identity_denials_to_gateway_reasons(
    gateway_settings: Settings, database: Database, clock: FakeClock
) -> None:
    grant = AgentGrant(
        agent_id="agent-soporte",
        version="1.0.0",
        department="soporte",
        scopes=("tool:get_order",),
        clearance=DataClassification.INTERNAL,
        allowed_regions=("cl",),
    )
    stage = IdentityStage(database.sessions, gateway_settings, clock)
    credential = CredentialIssuer(gateway_settings, clock).issue(grant)
    principal = await stage.authenticate(credential.token, "tool:get_order")
    assert principal.agent_id == "agent-soporte"
    async with database.sessions() as db:
        await RevocationService(db, clock).revoke_credential(principal.credential_id)
    with pytest.raises(GatewayDeniedError) as caught:
        await stage.authenticate(credential.token, "tool:get_order")
    assert caught.value.reason is GatewayReason.IDENTITY_REVOKED
    assert caught.value.stage is GatewayStage.IDENTITY
