from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.events.broker import EventBroker
from agent_zero.shared.database import Database


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    database: Database = request.app.state.database
    async with database.sessions() as session:
        yield session


def get_event_broker(request: Request) -> EventBroker:
    broker: EventBroker = request.app.state.event_broker
    return broker


DbSession = Annotated[AsyncSession, Depends(get_db_session)]
Broker = Annotated[EventBroker, Depends(get_event_broker)]
