from typing import Any

from pydantic import ValidationError

from agent_zero.agent_gateway.business_policy import BusinessDenial, CallContext
from agent_zero.policies.memory_rules import PREFERENCE_KEYS, changes_permissions
from agent_zero.policies.repository import PolicyRepository
from agent_zero.policies.validator_catalog import ValidatorName
from agent_zero.shared.database import Database
from agent_zero.victim.environments import Environment, Environments
from agent_zero.victim.fixtures import REFUND_LIMIT
from agent_zero.victim.tool_schemas import parse_arguments


class BusinessPolicyEngine:
    def __init__(self, database: Database, environments: Environments) -> None:
        self._database = database
        self._environments = environments

    async def check(
        self, context: CallContext, tool: str, arguments: dict[str, Any]
    ) -> BusinessDenial | None:
        try:
            parsed = parse_arguments(tool, arguments)
            async with self._database.sessions() as db:
                policy = await PolicyRepository(db).require(context.policy_version)
                rules = frozenset(ValidatorName(rule) for rule in policy.rules)
            environment = self._environments.for_context(context)
        except (KeyError, ValueError, ValidationError):
            return BusinessDenial("valid_call_context", "Contexto, versión o argumentos inválidos.")
        if context.operation_id and await environment.was_completed(context.operation_id):
            return None
        return await self._check_rules(context, tool, parsed, rules, environment)

    async def _check_rules(
        self,
        context: CallContext,
        tool: str,
        parsed: dict[str, Any],
        rules: frozenset[ValidatorName],
        environment: Environment,
    ) -> BusinessDenial | None:
        if tool in {"get_order", "request_refund"}:
            order = await environment.order(str(parsed["order_id"]))
            if order is None:
                return BusinessDenial("order_exists", "El pedido no existe.")
            if (
                ValidatorName.ORDER_OWNER in rules
                and order["customer_id"] != context.session_customer_id
            ):
                return BusinessDenial(
                    ValidatorName.ORDER_OWNER, "El pedido pertenece a otro cliente."
                )
            if tool == "request_refund" and ValidatorName.REFUND_LIMIT in rules:
                remaining = min(REFUND_LIMIT, float(order["total"])) - float(order["refunded"])
                if not 0 < float(parsed["amount"]) <= remaining:
                    return BusinessDenial(
                        ValidatorName.REFUND_LIMIT,
                        "El importe supera el límite o el saldo del pedido.",
                    )
        if (
            tool == "save_memory"
            and ValidatorName.MEMORY_KEYS in rules
            and (
                parsed["key"] not in PREFERENCE_KEYS
                or changes_permissions(str(parsed["key"]), str(parsed["value"]))
            )
        ):
            return BusinessDenial(
                ValidatorName.MEMORY_KEYS, "Solo se guardan preferencias sin cambios de permisos."
            )
        # Knowledge always comes from the server-owned collection with source identifiers.
        return None
