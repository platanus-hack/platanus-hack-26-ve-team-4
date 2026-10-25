import json
from functools import partial
from typing import Any

from sqlalchemy import select

from agent_zero.agent_gateway.business_policy import CallContext
from agent_zero.agent_gateway.schemas import ToolSpec
from agent_zero.agent_gateway.tool_registry import ToolOutput
from agent_zero.fleet.fleet_builder import Fleet
from agent_zero.identity.schemas import AgentPrincipal
from agent_zero.memory_bank.memory_read_service import MemoryReadService
from agent_zero.memory_bank.memory_write_service import MemoryWriteService
from agent_zero.memory_bank.models import MemoryKind
from agent_zero.memory_bank.schemas import MemoryWriteRequest
from agent_zero.shared.classification import DataClassification
from agent_zero.victim.controlled_fixtures import ControlledFixture
from agent_zero.victim.environments import Environment, Environments
from agent_zero.victim.fixture_outputs import contaminate, install_fixture
from agent_zero.victim.honeypot_view import session_order
from agent_zero.victim.knowledge_search import KnowledgeSearch, knowledge_output
from agent_zero.victim.model_view import without_internal_ids
from agent_zero.victim.operation_identity import operation_fingerprint
from agent_zero.victim.store_models import (
    ControlledFixtureRecord,
    StoreOperation,
    StoreOrder,
    StoreRefund,
)
from agent_zero.victim.tool_effects import replayed_operation, stored_operation, tool_output
from agent_zero.victim.tool_schemas import ARGUMENT_MODELS, parse_arguments
from agent_zero.victim.trace_schemas import (
    MemoryEffect,
    NoEffect,
    ReadEffect,
    RefundEffect,
    ToolEffect,
)


async def _context_required(arguments: dict[str, Any]) -> str:
    raise ValueError("Esta herramienta necesita un contexto del servidor.")


class ScenarioTools:
    def __init__(
        self,
        fleet: Fleet,
        environments: Environments,
        knowledge: KnowledgeSearch | None = None,
    ) -> None:
        self._fleet = fleet
        self._environments = environments
        self._knowledge = knowledge

    async def install_fixture(self, context: CallContext, fixture: ControlledFixture) -> None:
        await install_fixture(self._environments.for_context(context), context, fixture)

    async def fixtures(self, context: CallContext) -> tuple[ControlledFixture, ...]:
        async with self._environments.for_context(context).session() as db:
            rows = await db.scalars(
                select(ControlledFixtureRecord).where(
                    ControlledFixtureRecord.session_id == context.session_id
                )
            )
            return tuple(ControlledFixture.model_validate(row.data) for row in rows)

    def register(self) -> None:
        self._fleet.tools.register(
            ToolSpec(
                name="save_memory",
                classification=DataClassification.INTERNAL,
                region=self._fleet.settings.data_region,
                required_scope="tool:save_memory",
            ),
            _context_required,
        )
        for tool in ARGUMENT_MODELS:
            self._fleet.tools.bind_contextual(tool, partial(self.call, tool))

    async def call(
        self,
        tool: str,
        arguments: dict[str, Any],
        context: CallContext,
        principal: AgentPrincipal,
    ) -> ToolOutput:
        parsed = parse_arguments(tool, arguments)
        fingerprint = operation_fingerprint(tool, parsed, context.policy_version)
        environment = self._environments.for_context(context)
        if not context.operation_id:
            raise ValueError("Falta la identidad de la operación.")
        async with environment.session() as db:
            previous = await db.get(StoreOperation, context.operation_id)
            if previous is not None:
                if previous.fingerprint != fingerprint:
                    raise ValueError("La operación ya existe con otros argumentos o versión.")
                return replayed_operation(previous.output)
            effect: ToolEffect = NoEffect()
            if tool == "search_knowledge":
                output: dict[str, Any] = await knowledge_output(
                    str(parsed["query"]), environment.name, self._knowledge
                )
            elif tool == "save_memory":
                writer = MemoryWriteService(
                    db,
                    self._fleet.settings,
                    self._fleet.cipher,
                    self._fleet.memory_guard,
                    self._fleet.clock,
                )
                item = await writer.write(
                    principal,
                    MemoryWriteRequest(
                        subject_id=context.session_id,
                        kind=MemoryKind.PREFERENCE,
                        content=json.dumps(parsed, ensure_ascii=False),
                        source_run_id=context.run_id,
                    ),
                    commit=False,
                )
                output = {"saved": True, "memory_id": item.id, **parsed}
                effect = MemoryEffect(
                    memory_id=item.id, key=str(parsed["key"]), value=str(parsed["value"])
                )
            else:
                order = await db.get(StoreOrder, str(parsed["order_id"]))
                if order is None:
                    output = {"error": "pedido_inexistente"}
                elif tool == "get_order":
                    shown = session_order(environment.name, order.data, context.session_customer_id)
                    output = without_internal_ids(shown) | {"refunded": order.refunded_cents / 100}
                    effect = ReadEffect(
                        order_id=order.id, owner_customer_id=order.data["customer_id"]
                    )
                else:
                    cents = round(float(parsed["amount"]) * 100)
                    before = order.refunded_cents
                    db.add(
                        StoreRefund(
                            operation_id=context.operation_id,
                            order_id=order.id,
                            amount_cents=cents,
                            attempt_id=context.attempt_id,
                        )
                    )
                    order.refunded_cents += cents
                    output = {
                        "approved": True,
                        "order_id": order.id,
                        "amount": cents / 100,
                        "refunded_total": order.refunded_cents / 100,
                        "total": order.data["total"],
                        "canary": order.data["canary"],
                    }
                    effect = RefundEffect(
                        order_id=order.id,
                        owner_customer_id=order.data["customer_id"],
                        amount_cents=cents,
                        refunded_before_cents=before,
                        refunded_after_cents=order.refunded_cents,
                        total_cents=round(float(order.data["total"]) * 100),
                    )
            await contaminate(db, context, tool, output)
            db.add(
                StoreOperation(
                    id=context.operation_id,
                    output=stored_operation(output, effect),
                    fingerprint=fingerprint,
                )
            )
            await db.commit()
            return tool_output(output, effect)

    async def recall(
        self, environment: Environment, principal: AgentPrincipal, session_id: str
    ) -> list[str]:
        async with environment.database.sessions() as db:
            reader = MemoryReadService(
                db, self._fleet.cipher, self._fleet.memory_guard, self._fleet.clock
            )
            return [item.content for item in await reader.recall(principal, session_id, limit=8)]
