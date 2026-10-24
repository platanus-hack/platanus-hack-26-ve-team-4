from pathlib import Path

import pytest

from agent_zero.agent_gateway.models import GatewayReason
from agent_zero.agent_gateway.policy_engine import PolicyEngine
from agent_zero.agent_gateway.rate_limiter import RateLimiter
from agent_zero.agent_gateway.schemas import ToolSpec
from agent_zero.config import Settings
from agent_zero.identity.schemas import AgentPrincipal
from agent_zero.registry.schemas import ToolGrant
from agent_zero.shared.classification import DataClassification
from tests.identity.conftest import FakeClock


def principal(clearance: DataClassification = DataClassification.INTERNAL) -> AgentPrincipal:
    clock = FakeClock()
    return AgentPrincipal(
        credential_id="cred-1",
        agent_id="agente-soporte",
        version="1.0.0",
        department="soporte",
        scopes=("tool:get_order",),
        clearance=clearance,
        allowed_regions=("cl",),
        issued_at=clock(),
        expires_at=clock(),
    )


def spec(classification: DataClassification = DataClassification.INTERNAL) -> ToolSpec:
    return ToolSpec(
        name="get_order",
        classification=classification,
        region="cl",
        required_scope="tool:get_order",
    )


def grants(
    classification: DataClassification = DataClassification.INTERNAL,
) -> dict[str, ToolGrant]:
    return {
        "get_order": ToolGrant(name="get_order", description="d", classification=classification)
    }


@pytest.fixture
def engine(tmp_path: Path) -> PolicyEngine:
    settings = Settings(data_dir=tmp_path, allowed_data_regions=["cl"])
    return PolicyEngine(settings, RateLimiter(2, FakeClock()))


@pytest.mark.requirement("GW-02")
def test_allows_a_compliant_call(engine: PolicyEngine) -> None:
    assert engine.evaluate(principal(), spec(), grants(), None) is None


@pytest.mark.requirement("GW-02")
def test_no_manifest_means_not_approved(engine: PolicyEngine) -> None:
    assert engine.evaluate(principal(), spec(), None, None) is GatewayReason.AGENT_NOT_APPROVED


@pytest.mark.requirement("GW-02")
def test_manifest_grant_classification_also_counts(engine: PolicyEngine) -> None:
    reason = engine.evaluate(principal(), spec(), grants(DataClassification.CONFIDENTIAL), None)
    assert reason is GatewayReason.CLASSIFICATION_EXCEEDS_CLEARANCE


@pytest.mark.requirement("GW-02")
def test_higher_clearance_covers_lower_data(engine: PolicyEngine) -> None:
    assert engine.evaluate(principal(DataClassification.RESTRICTED), spec(), grants(), None) is None


@pytest.mark.requirement("GW-02")
def test_denied_static_checks_do_not_consume_the_budget(engine: PolicyEngine) -> None:
    for _ in range(5):
        engine.evaluate(principal(), spec(DataClassification.RESTRICTED), grants(), None)
    assert engine.evaluate(principal(), spec(), grants(), None) is None
    assert engine.evaluate(principal(), spec(), grants(), None) is None
    assert engine.evaluate(principal(), spec(), grants(), None) is GatewayReason.RATE_LIMITED
