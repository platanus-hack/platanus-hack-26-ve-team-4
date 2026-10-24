from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_zero.config import Settings
from agent_zero.events.broker import EventBroker
from agent_zero.events.router import router as events_router
from agent_zero.fleet.fleet_builder import build_fleet
from agent_zero.fleet.startup_guard import enforce_secure_settings
from agent_zero.fleet.tables import create_fleet_schema
from agent_zero.llm.factory import build_gateway
from agent_zero.memory_bank.router import router as memory_router
from agent_zero.registry.dependencies import OperatorOnly
from agent_zero.registry.router import router as registry_router
from agent_zero.runtime.router import router as runtime_router
from agent_zero.sessions.router import router as sessions_router
from agent_zero.shared.database import Database
from agent_zero.shared.health_router import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    enforce_secure_settings(settings)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    database = Database(settings.app_database_url)
    await create_fleet_schema(database)
    await database.create_schema()
    app.state.database = database
    app.state.event_broker = EventBroker()
    app.state.llm = build_gateway(settings)
    fleet = build_fleet(settings, database)
    app.state.fleet = fleet
    app.state.model_armor = fleet.armor
    app.state.audit_log = fleet.audit
    app.state.handler_registry = fleet.handlers
    app.state.tool_registry = fleet.tools
    fleet.start()
    try:
        yield
    finally:
        await fleet.stop()
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
    app.include_router(registry_router)
    app.include_router(runtime_router, dependencies=[OperatorOnly])
    app.include_router(memory_router)
    return app
