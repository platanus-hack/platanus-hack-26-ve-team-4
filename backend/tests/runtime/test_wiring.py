from agent_zero.runtime.handler_registry import HandlerRegistry
from agent_zero.runtime.wiring import RuntimeWiring
from agent_zero.shared.clock import utc_now
from agent_zero.shared.database import Database
from tests.runtime.support import FakeAdmission


def test_wiring_defaults(database: Database) -> None:
    wiring = RuntimeWiring(database.sessions, HandlerRegistry(), FakeAdmission())
    assert wiring.clock is utc_now
    assert wiring.telemetry is None
