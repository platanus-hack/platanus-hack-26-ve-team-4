import importlib.util
import random
import re
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "attack_swarm.py"


@pytest.fixture(scope="module")
def swarm() -> ModuleType:
    spec = importlib.util.spec_from_file_location("attack_swarm", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["attack_swarm"] = module
    spec.loader.exec_module(module)
    return module


def test_only_message_templates_travel_through_the_public_api(swarm: ModuleType) -> None:
    indices = swarm.usable_cases()

    assert indices
    assert len(indices) < swarm.CASES  # documento y resultado de herramienta necesitan fixtures.


@pytest.mark.parametrize("own", ["A-1001", "B-2001"])
def test_plans_only_mention_the_orders_of_the_simulated_session(
    swarm: ModuleType, own: str
) -> None:
    foreign = swarm.foreign_order(own)
    plans = swarm.plan_for(random.Random(7), swarm.usable_cases(), own, foreign, 30)

    assert plans
    for plan in plans:
        assert 1 <= len(plan.messages) <= 4
        mentioned = set(re.findall(r"\b[A-C]-\d{4}\b", " ".join(plan.messages)))
        assert mentioned <= {own, foreign}, plan


def test_plans_are_reproducible_with_a_seed(swarm: ModuleType) -> None:
    def build() -> list[list[str]]:
        plans = swarm.plan_for(random.Random(3), swarm.usable_cases(), "A-1001", "B-2001", 6)
        return [plan.messages for plan in plans]

    assert build() == build()


def test_agent_count_is_limited_to_four_through_six(swarm: ModuleType) -> None:
    for agents in (["--agents", "3"], ["--agents", "7"]):
        with pytest.raises(SystemExit):
            swarm.parse(agents)
    assert swarm.parse(["--agents", "5"]).agents == 5
