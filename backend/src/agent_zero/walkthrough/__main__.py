import argparse
import json
import os
import sys
from pathlib import Path

import httpx

from agent_zero.walkthrough.client import FleetClient
from agent_zero.walkthrough.walkthrough import run_walkthrough


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m agent_zero.walkthrough",
        description="Recorre los siete componentes de la flota contra un servidor en marcha.",
    )
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--secret", default=os.environ.get("AGENT_ZERO_OPERATOR_SECRET", ""))
    parser.add_argument("--follow-up-seconds", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--save", type=Path, help="guarda los runs completos en un JSON")
    return parser.parse_args()


def main() -> int:
    arguments = _arguments()
    if not arguments.secret:
        print("Falta el secreto de operador: --secret o AGENT_ZERO_OPERATOR_SECRET.")
        return 2
    with httpx.Client(base_url=arguments.base_url, timeout=30.0) as http:
        client = FleetClient(http, arguments.secret)
        report = run_walkthrough(client, arguments.follow_up_seconds, arguments.timeout)
    print(report.render())
    if arguments.save:
        arguments.save.write_text(
            json.dumps(report.runs, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
