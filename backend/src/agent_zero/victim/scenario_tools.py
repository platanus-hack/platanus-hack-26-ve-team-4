import json
from functools import partial
from typing import Any

from sqlalchemy import select

from agent_zero.agent_gateway.business_policy import CallContext
from agent_zero.agent_gateway.schemas import ToolSpec
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
from agent_zero.victim.knowledge import KNOWLEDGE
from agent_zero.victim.operation_identity import operation_fingerprint
from agent_zero.victim.store_models import (
    ControlledFixtureRecord,
    StoreOperation,
    StoreOrder,
    StoreRefund,
)
from agent_zero.victim.tool_schemas import ARGUMENT_MODELS, parse_arguments


async def _context_required(arguments: dict[str, Any]) -> str:
    raise ValueError("Esta herramienta necesita un contexto del servidor.")


class ScenarioTools:
    def __init__(self, fleet: Fleet, environments: Environments) -> None:
        self._fleet = fleet
        self._environments = environments

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
    ) -> str:
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
                return previous.output
            if tool == "search_knowledge":
                query = str(parsed["query"]).casefold()
                output: dict[str, Any] = {
                    "articles": [
                        {"text": article.answer, "source": f"knowledge:{article.slug}"}
                        for article in KNOWLEDGE
                        if any(word in query for word in article.keywords)
                    ],
                    "source": "knowledge:tienda",
                }
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
            else:
                order = await db.get(StoreOrder, str(parsed["order_id"]))
                if order is None:
                    output = {"error": "pedido_inexistente"}
                elif tool == "get_order":
                    output = dict(order.data) | {"refunded": order.refunded_cents / 100}
                else:
                    cents = round(float(parsed["amount"]) * 100)
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
                        "customer_id": order.data["customer_id"],
                        "amount": cents / 100,
                        "refunded_total": order.refunded_cents / 100,
                        "total": order.data["total"],
                        "canary": order.data["canary"],
                    }
            await contaminate(db, context, tool, output)
            encoded = json.dumps(output, ensure_ascii=False)
            db.add(StoreOperation(id=context.operation_id, output=encoded, fingerprint=fingerprint))
            await db.commit()
            return encoded

    async def recall(
        self, environment: Environment, principal: AgentPrincipal, session_id: str
    ) -> list[str]:
        async with environment.database.sessions() as db:
            reader = MemoryReadService(
                db, self._fleet.cipher, self._fleet.memory_guard, self._fleet.clock
            )
            return [item.content for item in await reader.recall(principal, session_id, limit=8)]
