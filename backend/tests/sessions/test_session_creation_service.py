from agent_zero.config import Settings
from agent_zero.routing.models import Route
from agent_zero.sessions.repository import SessionRepository
from agent_zero.sessions.schemas import SessionCreate
from agent_zero.sessions.session_creation_service import create_session
from agent_zero.shared.database import Database
from agent_zero.victim.fixtures import SYNTHETIC_CUSTOMER_IDS


async def test_new_session_starts_protected_with_synthetic_identity(settings: Settings) -> None:
    database = Database(settings.app_database_url)
    await database.create_schema()

    async with database.sessions() as db:
        created = await create_session(db, SessionCreate(alias="trinity"))

    async with database.sessions() as db:
        stored = await SessionRepository(db).get(created.id)

    await database.dispose()
    assert stored is not None
    assert stored.route is Route.PROTECTED
    assert stored.customer_id in SYNTHETIC_CUSTOMER_IDS
