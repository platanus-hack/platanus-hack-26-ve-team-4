import random
from collections.abc import Sequence
from dataclasses import dataclass

from agent_zero.prober.feedback import FailureSignal, SignalKind

Arm = tuple[str, str]
UNTRIED_PRIOR = 0.5
PROVEN_PRIOR = 1.0


@dataclass(frozen=True)
class Pull:
    arm: Arm
    version: int
    signal: FailureSignal

    @property
    def reward(self) -> bool:
        return self.signal.reward


class StrategySelector:
    def __init__(self, seed: str, epsilon: float = 0.25) -> None:
        self._seed = seed
        self._epsilon = epsilon

    def choose(self, arms: Sequence[Arm], history: Sequence[Pull], version: int) -> Arm | None:
        eligible = self._eligible(arms, history, version)
        if not eligible:
            return None
        rng = random.Random(f"{self._seed}:{len(history)}")
        if rng.random() < self._epsilon:
            return rng.choice(eligible)
        scores = {arm: self._score(arm, history, version) for arm in eligible}
        best = max(scores.values())
        return rng.choice([arm for arm in eligible if scores[arm] == best])

    def _eligible(self, arms: Sequence[Arm], history: Sequence[Pull], version: int) -> list[Arm]:
        spent = {
            pull.arm
            for pull in history
            if pull.version == version
            and pull.signal.kind in {SignalKind.VALIDATOR_DENIED, SignalKind.NO_TOOL}
        }
        return [arm for arm in arms if arm not in spent]

    def _score(self, arm: Arm, history: Sequence[Pull], version: int) -> float:
        current = [pull for pull in history if pull.arm == arm and pull.version == version]
        if current:
            return sum(pull.reward for pull in current) / len(current)
        proven = any(pull.arm == arm and pull.reward for pull in history)
        return PROVEN_PRIOR if proven else UNTRIED_PRIOR
