import asyncio
from typing import Any, cast

from agent_zero.contract.conditions import CallFacts, Exceeds
from agent_zero.contract.schema import PolicyRule
from agent_zero.guard.synthesizer import CandidatePolicy, GuardSynthesizer
from agent_zero.llm.gateway import LlmGateway
from agent_zero.llm.models import LlmMode
from tests.contract.support import shipped

BANK = shipped()["banco-transferencias"]
FACTS = CallFacts(
    "transferir",
    {"cuenta": "CTA-1", "destino": "BEN-AHORRO", "monto": 900, "concepto": "x"},
    "ana",
    {"monto": "user"},
    {"cuenta": "ana"},
)


def limit(value: float) -> PolicyRule:
    return PolicyRule(
        rule_id="r_llm",
        tool="transferir",
        deny_when=Exceeds(kind="exceeds", argument="monto", limit=value),
        reason="tope",
    )


class FakeLlm:
    def __init__(self, answer: CandidatePolicy | Exception) -> None:
        self.answer, self.calls = answer, 0

    async def structured(self, *_: Any) -> CandidatePolicy:
        self.calls += 1
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def propose(llm: FakeLlm, mode: LlmMode) -> tuple[list[PolicyRule], dict[str, Any]]:
    synthesizer = GuardSynthesizer(cast(LlmGateway, llm), mode)
    return asyncio.run(synthesizer.propose(BANK, [], BANK.violations(FACTS), FACTS))


def test_offline_modes_derive_rules_without_calling_the_model() -> None:
    llm = FakeLlm(CandidatePolicy(rules=[limit(500)], rationale="r"))
    rules, report = propose(llm, LlmMode.DEMO)
    assert llm.calls == 0
    assert report["source"] == "derived"
    assert report["gate"]["accepted"] is True
    assert rules


def test_live_keeps_a_model_policy_that_passes_the_gate() -> None:
    rules, report = propose(
        FakeLlm(CandidatePolicy(rules=[limit(450)], rationale="r")), LlmMode.LIVE
    )
    assert report["source"] == "synthesized"
    assert [rule.rule_id for rule in rules] == ["r_llm"]


def test_live_falls_back_when_the_model_breaks_legitimate_calls_or_fails() -> None:
    greedy = FakeLlm(CandidatePolicy(rules=[limit(10)], rationale="r"))
    _, report = propose(greedy, LlmMode.LIVE)
    assert report["source"] == "derived"
    assert report["rejected_gate"]["accepted"] is False
    _, failed = propose(FakeLlm(RuntimeError("caído")), LlmMode.LIVE)
    assert failed["source"] == "derived"
    assert failed["synthesis_error"] == "RuntimeError"


def test_live_adds_the_derived_floor_when_the_model_misses_the_injection() -> None:
    injected = CallFacts(
        "transferir",
        {"cuenta": "CTA-1", "destino": "BEN-AHORRO", "monto": 900, "concepto": "x"},
        "ana",
        {"monto": "untrusted", "destino": "untrusted"},
        {"cuenta": "ana"},
    )
    synthesizer = GuardSynthesizer(
        cast(LlmGateway, FakeLlm(CandidatePolicy(rules=[limit(500)], rationale="r"))),
        LlmMode.LIVE,
    )
    rules, report = asyncio.run(synthesizer.propose(BANK, [], BANK.violations(injected), injected))
    assert report["source"] == "synthesized"
    assert report["source_detail"] == "synthesized_with_derived_floor"
    assert report["weaker_than_floor"]["injected_blocked"] == 0
    assert report["gate"]["injected_blocked"] == report["gate"]["injected_total"]
    assert "r_llm" in [rule.rule_id for rule in rules]
    assert any(rule.deny_when.kind == "untrusted_origin" for rule in rules)
