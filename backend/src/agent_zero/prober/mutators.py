from collections.abc import Callable
from dataclasses import dataclass

from agent_zero.prober.mutator_channel import (
    can_chain,
    can_change_channel,
    chain,
    channel_document,
    channel_tool_result,
)
from agent_zero.prober.mutator_text import (
    can_split,
    paraphrase_en,
    paraphrase_es,
    split_turns,
)
from agent_zero.prober.schemas import AttackCase

Mutator = Callable[[AttackCase, str], AttackCase]


@dataclass(frozen=True)
class MutatorSpec:
    name: str
    applies: Callable[[AttackCase], bool]
    apply: Mutator


def _always(case: AttackCase) -> bool:
    return True


MUTATORS: dict[str, MutatorSpec] = {
    spec.name: spec
    for spec in (
        MutatorSpec("paraphrase_es", _always, paraphrase_es),
        MutatorSpec("paraphrase_en", _always, paraphrase_en),
        MutatorSpec("split_turns", can_split, split_turns),
        MutatorSpec("channel_document", can_change_channel, channel_document),
        MutatorSpec("channel_tool_result", can_change_channel, channel_tool_result),
        MutatorSpec("chain", can_chain, chain),
    )
}


def applicable(case: AttackCase) -> list[str]:
    return [name for name, spec in MUTATORS.items() if spec.applies(case)]


def mutate(name: str, case: AttackCase, customer: str) -> AttackCase:
    spec = MUTATORS[name]
    if not spec.applies(case):
        raise ValueError(f"El mutador {name} no aplica a este caso.")
    mutated = spec.apply(case, customer)
    return AttackCase.model_validate(
        mutated.model_dump()
        | {
            "case_id": f"{case.case_id}.{name}"[:120],
            "parent_case_id": case.case_id,
            "mutator": name,
        }
    )
