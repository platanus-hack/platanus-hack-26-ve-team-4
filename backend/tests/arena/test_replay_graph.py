from agent_zero.patches.replay_graph import build_graph, violation_effects
from tests.arena.replay_support import evidence, violated

OWNER = "order_belongs_to_session_customer"


def test_before_graph_marks_the_effect_and_after_cuts_the_edge() -> None:
    calls = [evidence(3, "get_order")]
    effects = violation_effects(violated(3))
    before = build_graph(calls, effects)
    after = build_graph(calls, effects, {3: OWNER})
    assert [node["kind"] for node in before["nodes"]] == ["agent", "tool", "effect"]
    assert before["edges"][-1]["state"] == "effect"
    assert before["nodes"][-1]["effect"] == "foreign_order_read"
    assert after["edges"][-1] == {
        "from": "tool-0",
        "to": "effect-0",
        "state": "blocked",
        "control": OWNER,
    }
    assert after["nodes"][-1]["state"] == "prevented"


def test_allowed_calls_stay_ok_and_denied_events_are_not_drawn() -> None:
    calls = [evidence(1, "search_knowledge"), evidence(2, "get_order", "tool_denied")]
    graph = build_graph(calls, {}, {})
    assert [node["label"] for node in graph["nodes"]] == ["Agente de soporte", "search_knowledge"]
    assert all(edge["state"] == "ok" for edge in graph["edges"])


def test_graph_exposes_no_arguments_outputs_or_canaries() -> None:
    calls = [evidence(3, "get_order")]
    text = str(build_graph(calls, violation_effects(violated(3)), {3: "unknown_control"}))
    assert "B-2001" not in text
    assert "cust-" not in text
    assert "AZP_" not in text
    assert "unknown_control" not in text


def test_unknown_tool_names_are_neutralised() -> None:
    graph = build_graph([evidence(1, "get_order; AZP_x")], {})
    assert graph["nodes"][1]["label"] == "herramienta"


def test_only_the_second_split_refund_is_cut() -> None:
    calls = [evidence(1, "request_refund"), evidence(2, "request_refund")]
    effects = violation_effects(violated(2, "OBJ-REFUND"))
    graph = build_graph(calls, effects, {1: None, 2: "refund_within_limit"})
    effect_edges = [edge for edge in graph["edges"] if edge["to"].startswith("effect")]
    assert [edge["state"] for edge in effect_edges] == ["blocked"]
    assert len([node for node in graph["nodes"] if node["kind"] == "tool"]) == 2
