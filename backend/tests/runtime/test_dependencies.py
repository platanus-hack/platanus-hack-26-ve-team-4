from fastapi import FastAPI
from starlette.requests import Request

from agent_zero.runtime.dependencies import get_runtime_clock
from agent_zero.shared.clock import utc_now


def test_runtime_clock_defaults_to_utc_now() -> None:
    app = FastAPI()
    request = Request({"type": "http", "app": app, "headers": []})
    assert get_runtime_clock(request) is utc_now
