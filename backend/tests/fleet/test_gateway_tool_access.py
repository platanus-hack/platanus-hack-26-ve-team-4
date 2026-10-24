import pytest

from agent_zero.agent_gateway.errors import GatewayDeniedError
from agent_zero.agent_gateway.models import GatewayReason
from agent_zero.agent_gateway.schemas import ToolSpec
from agent_zero.config import Settings
from agent_zero.fleet.fleet_builder import build_fleet
from agent_zero.fleet.gateway_tool_access import GatewayToolProvider
from agent_zero.fleet.token_vault import TokenNotFoundError, TokenVault
from agent_zero.registry.grant_service import grant_for
from agent_zero.shared.classification import DataClassification
from agent_zero.shared.database import Database
from tests.agent_gateway.support import build_manifest
from tests.fleet.support import publish_approved
from tests.identity.conftest import FakeClock


async def order_tool(arguments: dict[str, object]) -> str:
    return f"Pedido {arguments['order_id']} en camino."


@pytest.mark.requirement("GW-01")
async def test_provider_binds_the_token_of_the_principal(
    fleet_settings: Settings, database: Database, clock: FakeClock
) -> None:
    fleet = build_fleet(fleet_settings, database, clock)
    spec = ToolSpec(
        name="get_order",
        classification=DataClassification.INTERNAL,
        region="cl",
        required_scope="tool:get_order",
    )
    fleet.tools.register(spec, order_tool)
    await publish_approved(fleet, build_manifest())
    principal = await fleet.admission.admit("agente-soporte", "1.0.0")
    vault = TokenVault(clock)
    async with database.sessions() as db:
        grant = await grant_for(db, "agente-soporte", "1.0.0")
    credential = fleet.issuer.issue(grant)
    vault.put(credential)
    access = GatewayToolProvider(fleet.gateway, vault).tools_for(credential.principal)
    assert await access.call_tool("get_order", {"order_id": "A-1"}) == "Pedido A-1 en camino."
    with pytest.raises(GatewayDeniedError) as caught:
        await access.call_tool("get_ledger", {})
    assert caught.value.reason is GatewayReason.TOOL_UNREGISTERED
    with pytest.raises(TokenNotFoundError):
        GatewayToolProvider(fleet.gateway, TokenVault(clock)).tools_for(principal)
    await fleet.stop()
