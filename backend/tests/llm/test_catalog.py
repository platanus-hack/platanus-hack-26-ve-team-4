from pathlib import Path

from agent_zero.config import Settings
from agent_zero.llm.catalog import ROLE_PROFILES, model_for, profile_for
from agent_zero.llm.models import ModelRole


def test_every_role_has_a_profile() -> None:
    assert set(ROLE_PROFILES) == set(ModelRole)


def test_roles_default_to_haiku_and_accept_overrides(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, llm_role_models={"analyzer": "claude-sonnet-5-5"})

    assert model_for(ModelRole.PROBER, settings) == "claude-haiku-5-5"
    assert model_for(ModelRole.ANALYZER, settings) == "claude-sonnet-5-5"


def test_bulk_roles_use_low_effort() -> None:
    assert profile_for(ModelRole.PROBER).effort == "low"
    assert profile_for(ModelRole.VICTIM).effort == "low"
