import argparse
import asyncio
import json
import os
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import httpx

from agent_zero.loadtest.operator_api import operator_rows
from agent_zero.loadtest.participant import AttemptRecord, Pace, run_participant
from agent_zero.loadtest.report import percentile

MAX_ATTEMPTS = 1000


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Control de usuarios honestos: consultas legítimas durante una ronda en vivo."
    )
    parser.add_argument("--base", default="http://127.0.0.1:8080")
    parser.add_argument("--participants", type=int, default=10)
    parser.add_argument("--duration", type=float, default=240.0)
    parser.add_argument("--think", type=float, default=20.0)
    parser.add_argument("--alias-prefix", default="control-honesto")
    parser.add_argument("--insecure", action="store_true")
    parser.add_argument("--out", type=Path)
    return parser.parse_args()


def control_summary(records: list[AttemptRecord], attempts: list[dict[str, Any]]) -> dict[str, Any]:
    private = {row["id"]: row for row in attempts}
    by_version: dict[int, Counter[str]] = defaultdict(Counter)
    blocked: list[dict[str, Any]] = []
    misrouted = 0
    for record in records:
        row = private.get(record.attempt_id or "")
        if row is None:
            continue
        outcome = str(row.get("outcome"))
        by_version[int(row["policy_version"])][outcome] += 1
        if outcome == "prevented":
            blocked.append(
                {"id": row["id"], "family": record.family, "policy_version": row["policy_version"]}
            )
        misrouted += row.get("route") == "honeypot"
    latencies = [record.latency for record in records if record.latency is not None]
    joins = [record for record in records if record.kind == "join"]
    return {
        "participants_joined": len({record.participant for record in records}) - len(joins),
        "join_errors": [error for record in joins for error in record.errors],
        "attempts": len(records) - len(joins),
        "outcomes_by_policy_version": {
            str(key): dict(value) for key, value in sorted(by_version.items())
        },
        "false_blocks": len(blocked),
        "false_block_attempts": blocked,
        "routed_to_honeypot": misrouted,
        "inconclusive": sum(record.status == "inconclusive" for record in records),
        "timeouts": sum(record.status == "timeout" for record in records),
        "errors": dict(Counter(error for record in records for error in record.errors)),
        "latency_p50": percentile(latencies, 0.5),
        "latency_p95": percentile(latencies, 0.95),
    }


async def main() -> dict[str, Any]:
    args = arguments()
    secret = os.environ["AGENT_ZERO_OPERATOR_SECRET"]
    pace = Pace(MAX_ATTEMPTS, args.think, time.monotonic() + args.duration)
    limits = httpx.Limits(max_connections=args.participants + 5)
    async with httpx.AsyncClient(
        base_url=args.base, timeout=30, limits=limits, verify=not args.insecure
    ) as client:
        batches = await asyncio.gather(
            *(
                run_participant(client, f"{args.alias_prefix}-{index}", pace, index, "honest")
                for index in range(args.participants)
            )
        )
        attempts = await operator_rows(client, secret, "/api/operator/attempts")
    records = [record for batch in batches for record in batch]
    report = {"base": args.base, "duration_seconds": args.duration}
    report |= control_summary(records, attempts)
    if args.out:
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(asyncio.run(main()), ensure_ascii=False, indent=2))
