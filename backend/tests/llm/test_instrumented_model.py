from datetime import date

import pytest

from agent_zero.llm.context import call_scope
from agent_zero.llm.errors import ModelLimitReachedError, ModelRefusedError
from agent_zero.llm.instrumented_model import InstrumentedModel
from agent_zero.llm.ledger import MemoryCallLedger
from agent_zero.llm.limits import LimitPolicy, ModelLimits
from agent_zero.llm.models import CallKind, CallOutcome, LimitReason
from agent_zero.llm.playback_model import PlaybackModel, Refusal, ScriptEntry
from agent_zero.llm.quota import InMemoryCallQuota
from agent_zero.llm.schemas import CallUsage
from tests.llm.streams import PROMPT, Verdict, drain, output_of, text_of

USAGE = CallUsage(input_tokens=200, output_tokens=50)


def limits(session_calls: int = 10) -> ModelLimits:
    policy = LimitPolicy(
        daily_calls=100,
        session_calls=session_calls,
        campaign_calls=100,
        campaign_tokens=10_000,
        breaker_failures=3,
        breaker_recovery_seconds=30,
    )
    return ModelLimits(policy, InMemoryCallQuota(), lambda: 0.0, lambda: date(2026, 10, 24))


def instrumented(
    script: list[ScriptEntry], model_limits: ModelLimits | None = None
) -> tuple[InstrumentedModel, MemoryCallLedger]:
    ledger = MemoryCallLedger()
    inner = PlaybackModel(script, model_id="claude-haiku-5-5", usage=USAGE)
    return InstrumentedModel(inner, "victim", ledger, model_limits), ledger


async def test_successful_stream_is_recorded_with_cost_and_scope() -> None:
    model, ledger = instrumented(["hola"])

    with call_scope(session_id="sess-1", attempt_id="att-1"):
        events = await drain(model.stream(PROMPT))

    [record] = ledger.records()
    assert text_of(events) == "hola"
    assert record.outcome is CallOutcome.OK
    assert record.usage == USAGE
    assert record.cost is not None
    assert record.scope.attempt_id == "att-1"


async def test_structured_output_is_recorded_with_its_model() -> None:
    model, ledger = instrumented([{"label": "ok"}])

    output = output_of(await drain(model.structured_output(Verdict, PROMPT)))

    [record] = ledger.records()
    assert output == Verdict(label="ok")
    assert record.kind is CallKind.STRUCTURED
    assert record.output_model == "Verdict"


@pytest.mark.parametrize("structured", [False, True])
async def test_refusals_raise_a_dedicated_error(structured: bool) -> None:
    model, ledger = instrumented([Refusal()], limits())
    call = model.structured_output(Verdict, PROMPT) if structured else model.stream(PROMPT)

    with pytest.raises(ModelRefusedError):
        await drain(call)

    assert ledger.records()[0].outcome is CallOutcome.REFUSED
    assert ledger.records()[0].stop_reason == "refusal"


async def test_transient_failure_becomes_provider_unavailable() -> None:
    model, ledger = instrumented([TimeoutError("lento")])

    with pytest.raises(ModelLimitReachedError) as denial:
        await drain(model.stream(PROMPT))

    assert denial.value.reason is LimitReason.PROVIDER_UNAVAILABLE
    assert ledger.records()[0].outcome is CallOutcome.FAILED
    assert ledger.records()[0].error == "TimeoutError"


async def test_permanent_failure_is_raised_unchanged() -> None:
    model, ledger = instrumented([KeyError("mal")])

    with pytest.raises(KeyError):
        await drain(model.stream(PROMPT))

    assert ledger.records()[0].outcome is CallOutcome.FAILED


async def test_denied_call_is_recorded_without_reaching_the_model() -> None:
    model, ledger = instrumented(["uno", "dos"], limits(session_calls=1))

    with call_scope(session_id="sess-1"):
        await drain(model.stream(PROMPT))
        with pytest.raises(ModelLimitReachedError):
            await drain(model.stream(PROMPT))

    assert [record.outcome for record in ledger.records()] == [
        CallOutcome.OK,
        CallOutcome.DENIED,
    ]
    assert ledger.records()[1].error == "session_ceiling"
