from agent_zero.contract.conditions import CallFacts
from agent_zero.guard.derivation import derived_rules, merge
from tests.contract.support import shipped

BANK = shipped()["banco-transferencias"]


def test_a_broken_invariant_covers_every_tool_it_names() -> None:
    facts = CallFacts("consultar_saldo", {"cuenta": "CTA-9"}, "ana", {}, {"cuenta": "bruno"})
    rules = derived_rules(BANK, BANK.violations(facts), facts)
    assert sorted(rule.tool for rule in rules) == ["consultar_saldo", "transferir"]
    assert {rule.deny_when.kind for rule in rules} == {"not_owner"}


def test_low_integrity_arguments_of_side_effects_get_an_origin_rule() -> None:
    arguments = {"cuenta": "CTA-1", "destino": "BEN-X", "monto": 900, "concepto": "x"}
    provenance = {"cuenta": "user", "destino": "untrusted", "monto": "memory", "concepto": "model"}
    facts = CallFacts("transferir", arguments, "ana", provenance, {"cuenta": "ana"})
    rules = derived_rules(BANK, BANK.violations(facts), facts)
    origin = sorted(r.deny_when.argument for r in rules if r.deny_when.kind == "untrusted_origin")
    assert origin == ["destino", "monto"]
    assert all(rule.rule_id.startswith("r_") and len(rule.rule_id) <= 60 for rule in rules)


def test_read_only_tools_get_no_origin_rule_and_merge_dedupes() -> None:
    facts = CallFacts(
        "consultar_saldo", {"cuenta": "C"}, "ana", {"cuenta": "untrusted"}, {"cuenta": "b"}
    )
    rules = derived_rules(BANK, BANK.violations(facts), facts)
    assert all(rule.deny_when.kind != "untrusted_origin" for rule in rules)
    assert merge(rules, rules) == rules
