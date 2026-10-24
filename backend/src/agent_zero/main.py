from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_zero.arena.core import ProductCore
from agent_zero.arena.monitor_router import router as monitor_router
from agent_zero.arena.operator_router import router as operator_router
from agent_zero.arena.replay_router import router as replay_router
from agent_zero.arena.reset_router import router as reset_router
from agent_zero.arena.router import router as arena_router
from agent_zero.attempts.router import router as attempts_router
from agent_zero.config import Settings
from agent_zero.decoy.router import router as decoy_router
from agent_zero.evals.curve_router import router as coevolution_router
from agent_zero.evals.router import router as evaluations_router
from agent_zero.events.broker import EventBroker
from agent_zero.events.router import router as events_router
from agent_zero.fleet.fleet_builder import build_fleet
from agent_zero.fleet.router import router as fleet_router
from agent_zero.fleet.startup_guard import enforce_secure_settings
from agent_zero.fleet.tables import create_fleet_schema
from agent_zero.guard.container import build_guard
from agent_zero.guard.router import router as guard_router
from agent_zero.live.router import router as live_router
from agent_zero.llm.factory import build_gateway
from agent_zero.llm.models import ModelRole
from agent_zero.llm.playback_model import PlaybackModel
from agent_zero.memory_bank.router import router as memory_router
from agent_zero.prober.router import router as prober_router
from agent_zero.registry.dependencies import OperatorOnly
from agent_zero.registry.router import router as registry_router
from agent_zero.runtime.router import router as runtime_router
from agent_zero.sessions.router import router as sessions_router
from agent_zero.shared.database import Database, ensure_database
from agent_zero.shared.health_router import router as health_router
from agent_zero.victim.registration import register_victim


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    enforce_secure_settings(settings)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    await ensure_database(settings.app_database_url)
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
    core = ProductCore(fleet, app.state.llm, app.state.event_broker)
    await core.initialize()
    app.state.core = core
    app.state.guard = build_guard(settings, database, app.state.llm)
    fleet.start()
    core.worker.start()
    try:
        yield
    finally:
        await core.worker.stop()
        await fleet.stop()
        await core.dispose_stores()
        await database.dispose()


def create_app(
    settings: Settings | None = None,
    llm_playback: Mapping[ModelRole, PlaybackModel] | None = None,
) -> FastAPI:
    app = FastAPI(title="Agent Zero", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings or Settings()
    app.state.llm_playback = llm_playback
    if app.state.settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=app.state.settings.cors_origins,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )
    app.include_router(health_router)
    app.include_router(sessions_router)
    app.include_router(attempts_router)
    app.include_router(arena_router)
    app.include_router(replay_router)
    app.include_router(coevolution_router)
    app.include_router(reset_router)
    app.include_router(operator_router)
    app.include_router(monitor_router)
    app.include_router(evaluations_router)
    app.include_router(decoy_router)
    app.include_router(live_router)
    app.include_router(prober_router)
    app.include_router(events_router)
    app.include_router(registry_router)
    app.include_router(runtime_router, dependencies=[OperatorOnly])
    app.include_router(memory_router)
    app.include_router(fleet_router)
    app.include_router(guard_router)
    return app
