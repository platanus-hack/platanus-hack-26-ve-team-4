import asyncio
import json

import httpx

from agent_zero.loadtest.guard_load import GuardSample, guard_request, run_guard_load


def test_requests_alternate_and_use_distinct_subjects() -> None:
    legit_kind, legit = guard_request(0)
    attack_kind, attack = guard_request(1)
    assert (legit_kind, attack_kind) == ("legit", "attack")
    assert legit["subject"] != attack["subject"]
    assert attack["context"][-1]["origin"] == "untrusted"


def test_run_guard_load_records_every_answer() -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["subject"].endswith("-3"):
            return httpx.Response(503)
        allowed = body["arguments"]["monto"] < 500
        return httpx.Response(200, json={"allowed": allowed, "rule_id": None if allowed else "r"})

    async def run() -> list[GuardSample]:
        transport = httpx.MockTransport(answer)
        async with httpx.AsyncClient(transport=transport, base_url="http://guard") as client:
            return list(await run_guard_load(client, "k", 6, 2))

    samples = asyncio.run(run())
    assert len(samples) == 6
    assert [sample.status for sample in samples].count(503) == 1
