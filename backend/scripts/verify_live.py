"""Run the real provider through the laboratory, preserving every observed outcome.

uv run python scripts/verify_live.py --diagnostic-doh
The optional DNS diagnostic follows Cloudflare's documented DNS JSON interface:
https://developers.cloudflare.com/1.1.1.1/encryption/dns-over-https/make-api-requests/dns-json/
"""

import argparse
import tempfile
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from live_flow import verify
from live_support import LiveHarness, diagnostic_dns, export_artifact

from agent_zero.config import Settings
from agent_zero.llm.catalog import model_for
from agent_zero.llm.models import LlmMode, ModelRole
from agent_zero.llm.pricing import price_for
from agent_zero.main import create_app


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Verifica el núcleo con el proveedor real y presupuesto acotado."
    )
    parser.add_argument(
        "--diagnostic-doh",
        action="store_true",
        help="Diagnóstico explícito DNS DoH, sólo en este proceso para api.anthropic.com.",
    )
    parser.add_argument("--budget-usd", type=float, default=0.50)
    parser.add_argument(
        "--output", type=Path, default=root / "artifacts/core-evaluation/live-p0.json"
    )
    arguments = parser.parse_args()
    if not 0 < arguments.budget_usd <= 0.50:
        parser.error("El presupuesto debe estar en (0, 0.50] USD.")
    source = Settings(_env_file=root / ".env")
    if not source.llm_api_key.get_secret_value():
        parser.error(
            "Falta AGENT_ZERO_LLM_API_KEY en la configuración; no se usará un proveedor simulado."
        )
    artifact: dict[str, Any] = {"llm_mode": "live", "checks": {}, "errors": []}
    harness = None
    with tempfile.TemporaryDirectory(prefix="agent-zero-live-") as directory:
        settings = source.model_copy(
            update={
                "environment": "test",
                "data_dir": Path(directory),
                "llm_mode": LlmMode.LIVE,
                "llm_daily_usd_limit": min(arguments.budget_usd, source.llm_daily_usd_limit),
                "llm_daily_call_limit": 200,
                "llm_campaign_call_limit": 100,
                "llm_timeout_seconds": 30,
                "llm_retry_attempts": 1,
                "runtime_poll_seconds": 0.01,
                "arena_auto_patch": True,
                "gateway_rate_limit_per_minute": 10000,
            }
        )
        try:
            for role in ModelRole:
                price_for(model_for(role, settings))
            with (
                diagnostic_dns(arguments.diagnostic_doh) as dns,
                TestClient(create_app(settings)) as client,
            ):
                harness = LiveHarness(client, settings)
                artifact = harness.artifact
                artifact["dns_diagnostic"] = dns
                try:
                    verify(harness)
                finally:
                    if "reset_archive" not in artifact:
                        harness.collect()
        except Exception as failure:
            artifact["errors"].append(
                {
                    "type": type(failure).__name__,
                    "detail": str(failure)
                    if type(failure).__name__ == "LiveVerificationError"
                    else "",
                }
            )
            print(f"LIVE verificación detenida: {type(failure).__name__}", flush=True)
        finally:
            if harness is not None:
                harness.ledger()
            artifact["passed"] = (
                not artifact["errors"]
                and bool(artifact["checks"])
                and artifact.get("live_execution_verified", False)
                and artifact.get("within_budget", False)
            )
            export_artifact(artifact, arguments.output)
    print(
        f"LIVE evidencia: {arguments.output}; coste estimado: {artifact.get('known_cost_usd')}",
        flush=True,
    )
    if not artifact["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
