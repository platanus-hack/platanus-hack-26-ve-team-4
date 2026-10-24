"""Budgeted operator CLI: python -m agent_zero.evals --after 1 --output report.json."""

import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _request(base: str, secret: str, path: str, body: dict[str, Any] | None = None) -> Any:
    request = urllib.request.Request(
        base.rstrip("/") + "/api/operator/evaluations" + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"X-Operator-Secret": secret, "Content-Type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = json.loads(error.read().decode()).get("detail", error.reason)
        raise SystemExit(f"El servidor rechazó la operación ({error.code}): {detail}") from error
    except urllib.error.URLError as error:
        raise SystemExit(f"No se pudo conectar con {base}: {error.reason}") from error


def _export(payload: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(output)
    digest = hashlib.sha256(data).hexdigest()
    output.with_suffix(output.suffix + ".sha256").write_text(
        f"{digest}  {output.name}\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Evalúa 30 ataques y 15 tareas en dos políticas.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--operator-secret", default=os.environ.get("AGENT_ZERO_OPERATOR_SECRET", "change-me")
    )
    parser.add_argument("--before", type=int, default=0)
    parser.add_argument("--after", type=int)
    parser.add_argument("--repetitions", type=int, choices=(1, 2, 3), default=3)
    parser.add_argument("--max-calls", type=int, default=1200)
    parser.add_argument(
        "--evaluation-id", help="Reanuda la espera o exporta una evaluación existente."
    )
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if not arguments.evaluation_id and arguments.after is None:
        parser.error("--after es necesario al iniciar; --evaluation-id permite reanudar.")
    evaluation_id = arguments.evaluation_id
    if not evaluation_id:
        evaluation = _request(
            arguments.base_url,
            arguments.operator_secret,
            "",
            {
                "before_version": arguments.before,
                "after_version": arguments.after,
                "repetitions": arguments.repetitions,
                "max_calls": arguments.max_calls,
            },
        )
        evaluation_id = evaluation["id"]
        print(
            f"Evaluación {evaluation_id}: {evaluation['total']} ejecuciones planeadas.", flush=True
        )
    previous = -1
    while True:
        evaluations = _request(arguments.base_url, arguments.operator_secret, "")
        evaluation = next((row for row in evaluations if row["id"] == evaluation_id), None)
        if evaluation is None:
            raise SystemExit(f"La evaluación {evaluation_id} no existe en esta ronda.")
        if evaluation["completed"] != previous:
            previous = evaluation["completed"]
            print(f"{previous}/{evaluation['total']} — {evaluation['status']}", flush=True)
        if evaluation["status"] != "running" and evaluation["report"]:
            break
        time.sleep(1)
    payload = _request(arguments.base_url, arguments.operator_secret, f"/{evaluation_id}")
    _export(payload, arguments.output)
    report = payload["report"]
    print("Evidencia SIMULADA." if report["simulated"] else f"Origen: {report['evidence_origins']}")
    for version, metrics in report["versions"].items():
        attacks, tasks = metrics["adversarial"], metrics["legitimate"]
        print(
            f"Política {version}: {attacks['confirmed_violations']}/{attacks['evaluable']} "
            f"violaciones; {tasks['correct']}/{tasks['evaluable']} tareas correctas; "
            f"{attacks['inconclusive'] + tasks['inconclusive']} inconclusos."
        )
    print(f"Evidencia completa: {arguments.output}")
    if payload["status"] != "completed":
        raise SystemExit(f"La evaluación quedó parcial: {payload['stop_reason']}.")


if __name__ == "__main__":
    main()
