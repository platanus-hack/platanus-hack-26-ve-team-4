from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_zero.config import Settings
from agent_zero.events.broker import EventBroker
from agent_zero.events.router import router as events_router
from agent_zero.sessions.router import router as sessions_router
from agent_zero.shared.database import Database
from agent_zero.shared.health_router import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    database = Database(settings.app_database_url)
    await database.create_schema()
    app.state.database = database
    app.state.event_broker = EventBroker()
    yield
    await database.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="Agent Zero", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings or Settings()
    if app.state.settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=app.state.settings.cors_origins,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )
    app.include_router(health_router)
    app.include_router(sessions_router)
    app.include_router(events_router)
    return app
