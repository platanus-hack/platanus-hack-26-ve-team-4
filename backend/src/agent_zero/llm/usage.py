from collections.abc import Mapping
from typing import Any

from agent_zero.llm.schemas import CallUsage

INPUT_KEY = "inputTokens"
OUTPUT_KEY = "outputTokens"
TOTAL_KEY = "totalTokens"
CACHE_READ_KEY = "cacheReadInputTokens"
CACHE_WRITE_KEY = "cacheWriteInputTokens"
KNOWN_KEYS = frozenset({INPUT_KEY, OUTPUT_KEY, CACHE_READ_KEY, CACHE_WRITE_KEY})
WRAPPER_KEYS = ("event", "chunk")
REFUSAL = "refusal"


def _unwrapped(event: Any) -> Mapping[str, Any] | None:
    if not isinstance(event, Mapping):
        return None
    for key in WRAPPER_KEYS:
        inner = event.get(key)
        if isinstance(inner, Mapping):
            return inner
    return event


def _counted(usage: Mapping[str, Any], key: str) -> int:
    value = usage.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float) or value < 0:
        return 0
    return int(value)


def usage_from_event(event: Any) -> CallUsage | None:
    unwrapped = _unwrapped(event)
    metadata = unwrapped.get("metadata") if unwrapped is not None else None
    usage = metadata.get("usage") if isinstance(metadata, Mapping) else None
    if not isinstance(usage, Mapping) or not KNOWN_KEYS & set(usage):
        return None
    return CallUsage(
        input_tokens=_counted(usage, INPUT_KEY),
        output_tokens=_counted(usage, OUTPUT_KEY),
        cache_read_tokens=_counted(usage, CACHE_READ_KEY),
        cache_write_tokens=_counted(usage, CACHE_WRITE_KEY),
    )


def stop_reason_from_event(event: Any) -> str | None:
    unwrapped = _unwrapped(event)
    stop = unwrapped.get("messageStop") if unwrapped is not None else None
    reason = stop.get("stopReason") if isinstance(stop, Mapping) else None
    return reason if isinstance(reason, str) and reason else None


def usage_metadata(usage: CallUsage) -> dict[str, Any]:
    reported: dict[str, int] = {
        INPUT_KEY: usage.input_tokens,
        OUTPUT_KEY: usage.output_tokens,
        TOTAL_KEY: usage.total_tokens,
    }
    if usage.cache_read_tokens:
        reported[CACHE_READ_KEY] = usage.cache_read_tokens
    if usage.cache_write_tokens:
        reported[CACHE_WRITE_KEY] = usage.cache_write_tokens
    return {"metadata": {"usage": reported, "metrics": {"latencyMs": 0}}}
