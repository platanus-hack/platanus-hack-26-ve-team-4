from pydantic import BaseModel, ValidationError
from strands.models.model import Model
from strands.types.content import Messages

from agent_zero.llm.errors import StructuredOutputError

DEFAULT_REPAIR_BUDGET = 1

REPAIR_TEMPLATE = (
    "Tu respuesta anterior no cumplió el esquema {schema}. Error de validación: {error}. "
    "Responde de nuevo cumpliendo el esquema exactamente."
)


class MissingOutputError(ValueError):
    pass


async def _attempt[T: BaseModel](
    model: Model, output_model: type[T], prompt: Messages, system_prompt: str | None
) -> T:
    found: T | None = None
    async for event in model.structured_output(output_model, prompt, system_prompt=system_prompt):
        output = event.get("output")
        if isinstance(output, output_model):
            found = output
    if found is None:
        raise MissingOutputError(f"el modelo no devolvió {output_model.__name__}")
    return found


def _with_repair(prompt: Messages, output_model: type[BaseModel], error: Exception) -> Messages:
    note = REPAIR_TEMPLATE.format(schema=output_model.__name__, error=error)
    return [*prompt, {"role": "user", "content": [{"text": note}]}]


async def structured_call[T: BaseModel](
    model: Model,
    output_model: type[T],
    prompt: Messages,
    system_prompt: str | None = None,
    repair_budget: int = DEFAULT_REPAIR_BUDGET,
) -> T:
    if repair_budget < 0:
        raise ValueError("repair_budget no puede ser negativo")
    current = prompt
    last_error: Exception | None = None
    for attempt in range(repair_budget + 1):
        try:
            return await _attempt(model, output_model, current, system_prompt)
        except (ValidationError, MissingOutputError) as error:
            last_error = error
            current = _with_repair(prompt, output_model, error)
            if attempt == repair_budget:
                break
    raise StructuredOutputError(
        output_model.__name__,
        repair_budget + 1,
        last_error or MissingOutputError("sin intentos"),
    )
