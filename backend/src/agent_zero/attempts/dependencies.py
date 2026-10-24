from typing import Annotated

from fastapi import Depends, Request

from agent_zero.attempts.attempt_events import AttemptEvents
from agent_zero.attempts.attempt_submission_service import AttemptSubmissionService
from agent_zero.attempts.execution import ArenaWiring
from agent_zero.config import Settings
from agent_zero.events.broker import EventBroker
from agent_zero.runtime.handler_registry import HandlerRegistry
from agent_zero.shared.dependencies import DbSession


def get_submission_service(request: Request, db: DbSession) -> AttemptSubmissionService:
    settings: Settings = request.app.state.settings
    wiring: ArenaWiring = request.app.state.arena
    handlers: HandlerRegistry = request.app.state.handler_registry
    broker: EventBroker = request.app.state.event_broker
    return AttemptSubmissionService(db, settings, wiring, handlers, AttemptEvents(broker))


Submissions = Annotated[AttemptSubmissionService, Depends(get_submission_service)]
