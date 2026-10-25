from typing import Any

from agent_zero.agent_gateway.errors import GatewayDeniedError
from agent_zero.agent_gateway.models import GatewayReason

ORDER_TOOLS = frozenset({"get_order", "request_refund"})
ORDER_DENIAL_GUIDANCE = (
    "No se pudo usar ese pedido. Dile al cliente que revise el número y ofrece "
    "consultar uno de sus pedidos. No expliques si el pedido existe ni de quién es."
)


def denial_output(tool: str, denial: GatewayDeniedError) -> dict[str, Any]:
    output: dict[str, Any] = {"denied": denial.reason.value}
    if tool in ORDER_TOOLS and denial.reason is GatewayReason.BUSINESS_RULE_DENIED:
        output["guidance"] = ORDER_DENIAL_GUIDANCE
    return output
