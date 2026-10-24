from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from agent_zero.config import Settings
from agent_zero.llm.models import ModelRole
from agent_zero.llm.playback_model import PlaybackModel, ScriptEntry
from agent_zero.main import create_app
from agent_zero.walkthrough.client import FleetClient
from agent_zero.walkthrough.walkthrough import run_walkthrough

SECRET = "secreto-de-operador-para-pruebas"
REPLIES: list[ScriptEntry] = [
    "Tu pedido A-1001 va en camino y llega en 2 a 5 días hábiles.",
    "Lamento la falla; un agente revisará la devolución.",
]


def fleet_settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path,
        environment="test",
        operator_secret=SecretStr(SECRET),
        otel_exporter="memory",
        runtime_poll_seconds=0.05,
    )


@pytest.mark.requirement("DEMO-01")
def test_walkthrough_passes_against_the_real_app(tmp_path: Path) -> None:
    playback = {ModelRole.VICTIM: PlaybackModel(REPLIES, model_id="claude-haiku-5-5")}
    app = create_app(fleet_settings(tmp_path), playback)

    with TestClient(app) as http:
        report = run_walkthrough(FleetClient(http, SECRET, poll_seconds=0.05), 1, 20.0)

    assert report.ok, report.render()
