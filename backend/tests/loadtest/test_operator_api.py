import asyncio

import httpx
import pytest

from agent_zero.loadtest.operator_api import operator_rows


def test_operator_rows_sends_the_secret_and_fails_loudly() -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        if request.headers.get("X-Operator-Secret") != "s":
            return httpx.Response(401)
        return httpx.Response(200, json=[{"id": "a"}])

    async def call(secret: str) -> list[object]:
        transport = httpx.MockTransport(answer)
        async with httpx.AsyncClient(transport=transport, base_url="http://arena") as client:
            return await operator_rows(client, secret, "/api/operator/attempts")

    assert asyncio.run(call("s")) == [{"id": "a"}]
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(call("otro"))
