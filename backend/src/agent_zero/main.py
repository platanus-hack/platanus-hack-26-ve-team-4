from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_zero.attempts.arena_router import router as arena_state_router
from agent_zero.attempts.attempt_events import AttemptEvents
from agent_zero.attempts.attempt_tracker import AttemptTracker
from agent_zero.attempts.execution import ArenaWiring
from agent_zero.attempts.operator_router import router as attempts_operator_router
from agent_zero.attempts.router import router as attempts_router
from agent_zero.config import Settings
from agent_zero.events.broker import EventBroker
from agent_zero.events.router import router as events_router
from agent_zero.fleet.fleet_builder import build_fleet
from agent_zero.fleet.router import router as fleet_router
from agent_zero.fleet.startup_guard import enforce_secure_settings
from agent_zero.fleet.tables import create_fleet_schema
from agent_zero.llm.factory import build_gateway
from agent_zero.llm.models import ModelRole
from agent_zero.llm.playback_model import PlaybackModel
from agent_zero.memory_bank.router import router as memory_router
from agent_zero.registry.router import router as registry_router
from agent_zero.runtime.router import router as runtime_router
from agent_zero.sessions.operator_router import router as sessions_operator_router
from agent_zero.sessions.router import router as sessions_router
from agent_zero.shared.database import Database
from agent_zero.shared.health_router import router as health_router
from agent_zero.shared.operator_auth import OperatorOnly
from agent_zero.victim.registration import register_victim


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
    fleet = build_fleet(settings, database)
    app.state.llm = build_gateway(settings, app.state.llm_playback, tracer=fleet.telemetry.tracer)
    register_victim(fleet, app.state.llm)
    app.state.fleet = fleet
    app.state.model_armor = fleet.armor
    app.state.audit_log = fleet.audit
    app.state.handler_registry = fleet.handlers
    app.state.tool_registry = fleet.tools
    tracker = AttemptTracker(
        database.sessions,
        app.state.arena,
        AttemptEvents(app.state.event_broker),
        settings.runtime_poll_seconds,
    )
    app.state.attempt_tracker = tracker
    fleet.start()
    tracker.start()
    try:
        yield
    finally:
        await tracker.stop()
        await fleet.stop()
        await database.dispose()


def create_app(
    settings: Settings | None = None,
    llm_playback: Mapping[ModelRole, PlaybackModel] | None = None,
) -> FastAPI:
    app = FastAPI(title="Agent Zero", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings or Settings()
    app.state.llm_playback = llm_playback
    app.state.arena = ArenaWiring()
    if app.state.settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=app.state.settings.cors_origins,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )
    app.include_router(health_router)
    app.include_router(sessions_router)
    app.include_router(sessions_operator_router)
    app.include_router(attempts_router)
    app.include_router(attempts_operator_router)
    app.include_router(arena_state_router)
    app.include_router(events_router)
    app.include_router(registry_router)
    app.include_router(runtime_router, dependencies=[OperatorOnly])
    app.include_router(memory_router)
    app.include_router(fleet_router)
    return app
