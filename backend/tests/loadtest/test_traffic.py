import random

from agent_zero.loadtest.traffic import attack_task, foreign_order, legit_task, plan
from agent_zero.victim.fixtures import ORDERS, REFUND_LIMIT


def test_foreign_order_never_belongs_to_the_participant() -> None:
    rng = random.Random(1)
    own = ["A-1001"]
    assert all(foreign_order(own, rng) not in own for _ in range(50))
    assert all(foreign_order(own, rng) in ORDERS for _ in range(50))


def test_attacks_cover_four_families_and_exceed_the_refund_limit() -> None:
    rng = random.Random(2)
    tasks = [attack_task("A-1001", "B-2001", rng) for _ in range(80)]
    assert {task.family for task in tasks} == {
        "pedido_ajeno",
        "reembolso_excedido",
        "desvio_objetivo",
        "memoria",
    }
    refund = next(task for task in tasks if task.family == "reembolso_excedido")
    assert f"{REFUND_LIMIT * 3:g} USD" in refund.messages[0]
    assert all(task.kind == "attack" for task in tasks)


def test_legit_tasks_only_touch_the_own_order() -> None:
    rng = random.Random(3)
    tasks = [legit_task("A-1001", rng) for _ in range(40)]
    assert all("B-" not in " ".join(task.messages) for task in tasks)
    assert {task.kind for task in tasks} == {"legit"}


def test_plan_mixes_legit_and_attacks() -> None:
    rng = random.Random(4)
    kinds = [plan(["A-1001"], rng).kind for _ in range(200)]
    assert 40 < kinds.count("legit") < 120
