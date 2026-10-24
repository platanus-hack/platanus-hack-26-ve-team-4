from agent_zero.prober.feedback import FailureSignal, SignalKind
from agent_zero.prober.strategy_selector import Arm, Pull, StrategySelector

ORDER_SEED: Arm = ("OBJ-ORDER", "seed")
ORDER_CHAIN: Arm = ("OBJ-ORDER", "chain")
REFUND_SEED: Arm = ("OBJ-REFUND", "seed")
ARMS = [ORDER_SEED, ORDER_CHAIN, REFUND_SEED]
WIN = FailureSignal(SignalKind.VIOLATION)
BLOCK = FailureSignal(SignalKind.VALIDATOR_DENIED, validator="order_ownership")
NO_TOOL = FailureSignal(SignalKind.NO_TOOL)


def test_same_seed_gives_the_same_sequence() -> None:
    def run(seed: str) -> list[Arm | None]:
        selector = StrategySelector(seed)
        history: list[Pull] = []
        picks: list[Arm | None] = []
        for _ in range(12):
            arm = selector.choose(ARMS, history, 0)
            picks.append(arm)
            assert arm is not None
            history.append(
                Pull(arm, 0, WIN if arm == REFUND_SEED else FailureSignal(SignalKind.NOT_ACHIEVED))
            )
        return picks

    assert run("campaign-a") == run("campaign-a")
    assert any(run("campaign-a") != run(f"campaign-{n}") for n in range(8))


def test_arm_with_wins_in_this_version_is_preferred() -> None:
    selector = StrategySelector("seed", epsilon=0.0)
    history = [
        Pull(REFUND_SEED, 0, WIN),
        Pull(ORDER_SEED, 0, FailureSignal(SignalKind.NOT_ACHIEVED)),
    ]

    assert {selector.choose(ARMS, history, 0) for _ in range(5)} == {REFUND_SEED}


def test_arm_blocked_by_a_validator_is_not_repeated_in_that_version() -> None:
    selector = StrategySelector("seed", epsilon=1.0)
    history = [Pull(ORDER_SEED, 0, BLOCK), Pull(REFUND_SEED, 0, NO_TOOL)]

    for step in range(20):
        padded = history + [Pull(ORDER_CHAIN, 0, FailureSignal(SignalKind.NOT_ACHIEVED))] * step
        assert selector.choose(ARMS, padded, 0) == ORDER_CHAIN


def test_blocked_arms_become_available_again_in_a_new_version() -> None:
    selector = StrategySelector("seed", epsilon=0.0)
    history = [Pull(ORDER_SEED, 0, BLOCK)]

    assert selector.choose([ORDER_SEED], history, 0) is None
    assert selector.choose([ORDER_SEED], history, 1) == ORDER_SEED


def test_exploit_that_worked_before_is_retried_first_after_a_patch() -> None:
    selector = StrategySelector("seed", epsilon=0.0)
    history = [Pull(REFUND_SEED, 0, WIN)]

    assert selector.choose(ARMS, history, 1) == REFUND_SEED
