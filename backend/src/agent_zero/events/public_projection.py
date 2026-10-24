from agent_zero.events.schemas import TraceEvent

PUBLIC_FIELDS = frozenset({"status", "outcome", "finding_id", "objective_id", "version", "passed"})


def public_projection(event: TraceEvent) -> TraceEvent:
    return event.model_copy(
        update={
            "attempt_id": None,
            "session_id": None,
            "data": {key: value for key, value in event.data.items() if key in PUBLIC_FIELDS},
        }
    )
