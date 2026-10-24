from agent_zero.contract.conditions import CallFacts, Exceeds, UntrustedOrigin
from agent_zero.contract.schema import PolicyRule
from agent_zero.guard.enforcement import first_denial, gate, injected_probes
from tests.contract.support import shipped

YUMMY = shipped()["yummy-soporte"]
LIMIT = PolicyRule(
    rule_id="r_limit",
    tool="request_refund",
    deny_when=Exceeds(kind="exceeds", argument="amount", limit=20),
    reason="tope",
)
ORIGIN = PolicyRule(
    rule_id="r_origin",
    tool="request_refund",
    deny_when=UntrustedOrigin(kind="untrusted_origin", argument="amount"),
    reason="origen",
)
ATTACK = CallFacts(
    "request_refund", {"order_id": "A", "amount": 90}, "ana", {}, {"order_id": "ana"}
)


def test_first_denial_only_matches_its_own_tool() -> None:
    assert first_denial([LIMIT], ATTACK) == LIMIT
    other = CallFacts("get_order", {"amount": 90}, "ana")
    assert first_denial([LIMIT], other) is None


def test_gate_accepts_a_rule_that_blocks_the_attack_and_keeps_legitimate_calls() -> None:
    report = gate(YUMMY, [LIMIT], [ATTACK])
    assert report["accepted"] is True
    assert report["injected_total"] == 2
    assert report["injected_blocked"] == 0
    assert gate(YUMMY, [LIMIT, ORIGIN], [ATTACK])["injected_blocked"] == 2


def test_gate_rejects_a_rule_that_breaks_legitimate_calls() -> None:
    greedy = LIMIT.model_copy(
        update={"deny_when": Exceeds(kind="exceeds", argument="amount", limit=1)}
    )
    report = gate(YUMMY, [greedy], [ATTACK])
    assert report["accepted"] is False
    assert report["legitimate_kept"] < report["legitimate_total"]


def test_probes_taint_only_side_effect_tools() -> None:
    assert injected_probes(YUMMY, {"get_order"}) == []
    probes = injected_probes(YUMMY, {"request_refund"})
    assert all(set(probe.provenance.values()) == {"untrusted"} for probe in probes)
