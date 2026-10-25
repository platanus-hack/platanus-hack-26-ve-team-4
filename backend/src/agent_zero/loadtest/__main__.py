import argparse
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

from agent_zero.loadtest.guard_load import run_guard_load
from agent_zero.loadtest.participant import run_participant
from agent_zero.loadtest.report import guard_summary, load_summary, mission_summary

SETTLE_SECONDS = 180.0
PENDING = frozenset({"candidate", "validating"})


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prueba de estrés de la arena y del Guard.")
    parser.add_argument("--base", default="http://127.0.0.1:8080")
    parser.add_argument("--participants", type=int, default=30)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--think", type=float, default=3.0)
    parser.add_argument("--guard-checks", type=int, default=400)
    parser.add_argument("--guard-concurrency", type=int, default=20)
    parser.add_argument("--insecure", action="store_true")
    parser.add_argument("--out", type=Path)
    return parser.parse_args()


async def operator_rows(client: httpx.AsyncClient, secret: str, path: str) -> list[Any]:
    response = await client.get(path, headers={"X-Operator-Secret": secret})
    response.raise_for_status()
    rows: list[Any] = response.json()
    return rows


async def settled_policies(client: httpx.AsyncClient, secret: str) -> list[Any]:
    deadline = time.monotonic() + SETTLE_SECONDS
    while True:
        policies = await operator_rows(client, secret, "/api/operator/policies")
        pending = [row for row in policies if row.get("status") in PENDING]
        if not pending or time.monotonic() > deadline:
            return policies
        await asyncio.sleep(2)


async def main() -> dict[str, Any]:
    args = arguments()
    secret = os.environ["AGENT_ZERO_OPERATOR_SECRET"]
    guard_key = os.environ.get("AGENT_ZERO_GUARD_API_KEY", "change-me-guard")
    limits = httpx.Limits(max_connections=args.participants + args.guard_concurrency + 10)
    async with httpx.AsyncClient(
        base_url=args.base, timeout=30, limits=limits, verify=not args.insecure
    ) as client:
        state = (await client.get("/api/arena/state")).json()
        started = time.monotonic()
        batches = await asyncio.gather(
            *(
                run_participant(client, f"estres-{index}", args.attempts, args.think, index)
                for index in range(args.participants)
            )
        )
        arena_wall = time.monotonic() - started
        records = [record for batch in batches for record in batch]
        policies = await settled_policies(client, secret)
        attempts = await operator_rows(client, secret, "/api/operator/attempts")
        guard_started = time.monotonic()
        samples = await run_guard_load(client, guard_key, args.guard_checks, args.guard_concurrency)
        guard_wall = time.monotonic() - guard_started
    report = {
        "base": args.base,
        "llm_mode": state.get("llm_mode"),
        "participants": args.participants,
        "attempts_per_participant": args.attempts,
        "load": load_summary(records, arena_wall),
        "mission": mission_summary(records, attempts, policies),
        "guard": guard_summary(samples, guard_wall),
    }
    if args.out:
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(asyncio.run(main()), ensure_ascii=False, indent=2))
