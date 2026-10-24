from agent_zero.contract.attacks import violating_variant
from agent_zero.contract.conditions import CallFacts
from tests.contract.support import shipped


def test_every_invariant_of_every_contract_gets_a_breaking_variant() -> None:
    for contract in shipped().values():
        for invariant in contract.invariants:
            variant = violating_variant(contract, invariant)
            assert variant is not None, invariant.id
            base, arguments, provenance, owners = variant
            owners = {k: "ana" if v == "subject" else v for k, v in owners.items()}
            facts = CallFacts(base.tool, arguments, "ana", provenance, owners)
            assert invariant in contract.violations(facts), invariant.id
