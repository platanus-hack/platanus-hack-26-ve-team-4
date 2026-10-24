import pytest
from pydantic import ValidationError

from agent_zero.armor.models import ArmorAction, Surface, ThreatKind
from agent_zero.armor.schemas import ArmorFinding, ArmorVerdict


def test_finding_rejects_empty_detail() -> None:
    with pytest.raises(ValidationError):
        ArmorFinding(kind=ThreatKind.PII, surface=Surface.USER_INPUT, detail="")


def test_verdict_is_frozen_and_forbids_extra() -> None:
    verdict = ArmorVerdict(action=ArmorAction.ALLOW, sanitized_text="hola")
    assert verdict.model_config["frozen"]
    with pytest.raises(ValidationError):
        ArmorVerdict.model_validate({"action": "allow", "extra": 1})


def test_blocked_property() -> None:
    assert ArmorVerdict(action=ArmorAction.BLOCK).blocked
    assert not ArmorVerdict(action=ArmorAction.REDACT).blocked
