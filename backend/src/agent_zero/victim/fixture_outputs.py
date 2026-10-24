from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.agent_gateway.business_policy import CallContext
from agent_zero.victim.controlled_fixtures import ControlledFixture
from agent_zero.victim.environments import Environment
from agent_zero.victim.store_models import ControlledFixtureRecord


async def install_fixture(
    environment: Environment, context: CallContext, fixture: ControlledFixture
) -> None:
    await environment.ensure_customer(context.session_customer_id)
    async with environment.transaction(), environment.session() as db:
        identity = (context.session_id, fixture.surface, fixture.target_tool)
        existing = await db.get(ControlledFixtureRecord, identity)
        data = fixture.model_dump(mode="json")
        if existing is not None and existing.data != data:
            raise ValueError("La sesión ya tiene una superficie controlada diferente.")
        if existing is None:
            db.add(
                ControlledFixtureRecord(
                    session_id=context.session_id,
                    surface=fixture.surface,
                    target_tool=fixture.target_tool,
                    data=data,
                )
            )
        await db.commit()


async def contaminate(
    db: AsyncSession, context: CallContext, tool: str, output: dict[str, Any]
) -> None:
    records = await db.scalars(
        select(ControlledFixtureRecord).where(
            ControlledFixtureRecord.session_id == context.session_id,
            ControlledFixtureRecord.target_tool == tool,
        )
    )
    for record in records:
        fixture = ControlledFixture.model_validate(record.data)
        untrusted = {"text": fixture.content, "source": fixture.source, "trust": "untrusted"}
        if fixture.surface == "document" and tool == "search_knowledge":
            output["articles"] = [*output.get("articles", []), untrusted]
        else:
            output["untrusted_external_context"] = untrusted
