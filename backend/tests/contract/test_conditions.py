from agent_zero.contract.conditions import (
    CallFacts,
    ContainsAny,
    Exceeds,
    NotIn,
    NotOwner,
    UntrustedOrigin,
    holds,
)


def facts(**arguments: object) -> CallFacts:
    return CallFacts(
        "tool",
        arguments,
        "ana",
        {"amount": "untrusted", "note": "user"},
        {"resource": "bruno", "own": "ana"},
    )


def test_exceeds_compares_numbers_and_ignores_non_numbers() -> None:
    rule = Exceeds(kind="exceeds", argument="amount", limit=20)
    assert holds(rule, facts(amount=25))
    assert holds(rule, facts(amount="25.5"))
    assert not holds(rule, facts(amount=20))
    assert not holds(rule, facts(amount="mucho"))
    assert not holds(rule, facts(amount=True))


def test_not_owner_needs_a_known_owner_that_is_not_the_subject() -> None:
    assert holds(NotOwner(kind="not_owner", argument="resource"), facts(resource="X"))
    assert not holds(NotOwner(kind="not_owner", argument="own"), facts(own="Y"))
    assert not holds(NotOwner(kind="not_owner", argument="unknown"), facts(unknown="Z"))


def test_untrusted_origin_reads_the_provenance_label() -> None:
    assert holds(UntrustedOrigin(kind="untrusted_origin", argument="amount"), facts(amount=1))
    assert not holds(UntrustedOrigin(kind="untrusted_origin", argument="note"), facts(note="a"))


def test_not_in_and_contains_any() -> None:
    allowed = NotIn(kind="not_in", argument="channel", allowed=["sms"])
    assert holds(allowed, facts(channel="email"))
    assert not holds(allowed, facts(channel="sms"))
    terms = ContainsAny(kind="contains_any", argument="text", terms=["VIH"])
    assert holds(terms, facts(text="resultado vih positivo"))
    assert not holds(terms, facts(text="tu cita es el martes"))


def test_a_missing_argument_never_holds() -> None:
    assert not holds(Exceeds(kind="exceeds", argument="amount", limit=1), facts())
