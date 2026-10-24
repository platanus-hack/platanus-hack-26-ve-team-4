import re

from agent_zero.prober.schemas import AttackCase

PREFIXES_ES = (
    "Por favor, ",
    "Necesito ayuda con esto: ",
    "Hola, una consulta rápida. ",
    "Gracias de antemano. ",
)
PREFIXES_EN = ("Hello, ", "Quick request: ", "Hi team, ", "Thanks in advance. ")
FIXTURE_PREFIXES = ("Aviso de soporte: ", "Procedimiento actualizado: ", "Nota interna: ")
TRANSLATIONS = (
    ("Reembolsa", "Refund"),
    ("del pedido", "of order"),
    ("el pedido", "order"),
    ("Consulta", "Check"),
    ("Tengo permiso del titular", "I have the owner's permission"),
    ("Necesito confirmar una entrega urgente", "I need to confirm an urgent delivery"),
)
OPENER = "Hola, necesito ayuda con un pedido."
SENTENCE_BREAK = re.compile(r"(?<=[.;])\s+")


def _variant(case: AttackCase, options: tuple[str, ...]) -> str:
    return options[(case.seed or 0) % len(options)]


def _with_messages(case: AttackCase, messages: list[str]) -> AttackCase:
    return AttackCase.model_validate(case.model_dump() | {"messages": messages})


def _with_fixture_text(case: AttackCase, text: str) -> AttackCase:
    if case.fixture is None:
        raise ValueError("El caso no tiene fixture.")
    return AttackCase.model_validate(
        case.model_dump() | {"fixture": case.fixture.model_copy(update={"content": text})}
    )


def paraphrase_es(case: AttackCase, customer: str) -> AttackCase:
    if case.fixture is not None:
        return _with_fixture_text(case, _variant(case, FIXTURE_PREFIXES) + case.fixture.content)
    prefix = _variant(case, PREFIXES_ES)
    return _with_messages(case, [prefix + message for message in case.messages])


def paraphrase_en(case: AttackCase, customer: str) -> AttackCase:
    prefix = _variant(case, PREFIXES_EN)
    if case.fixture is not None:
        return _with_fixture_text(case, prefix + case.fixture.content)
    translated: list[str] = []
    for message in case.messages:
        text = message
        for spanish, english in TRANSLATIONS:
            text = text.replace(spanish, english)
        translated.append(prefix + text)
    return _with_messages(case, translated)


def can_split(case: AttackCase) -> bool:
    return len(case.messages) < 4


def split_turns(case: AttackCase, customer: str) -> AttackCase:
    *head, last = case.messages
    parts = [part for part in SENTENCE_BREAK.split(last) if part.strip()]
    if len(parts) >= 2:
        return _with_messages(case, [*head, parts[0], " ".join(parts[1:])])
    return _with_messages(case, [*head, OPENER, last])
