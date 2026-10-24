from agent_zero.contract.conditions import ContainsAny, Exceeds, NotIn, NotOwner, UntrustedOrigin
from agent_zero.contract.schema import PolicyRule
from agent_zero.guard.views import clause, render


def test_every_condition_renders_as_a_readable_clause() -> None:
    assert clause(Exceeds(kind="exceeds", argument="monto", limit=500)) == "monto > 500"
    assert "no pertenece" in clause(NotOwner(kind="not_owner", argument="cuenta"))
    assert "no confiable" in clause(UntrustedOrigin(kind="untrusted_origin", argument="monto"))
    assert "fuera de" in clause(NotIn(kind="not_in", argument="canal", allowed=["sms"]))
    assert "contiene" in clause(ContainsAny(kind="contains_any", argument="texto", terms=["VIH"]))


def test_render_names_the_tool() -> None:
    rule = PolicyRule(
        rule_id="r_x",
        tool="transferir",
        deny_when=Exceeds(kind="exceeds", argument="monto", limit=500),
        reason="tope",
    )
    assert render(rule) == "DENEGAR transferir SI monto > 500"
