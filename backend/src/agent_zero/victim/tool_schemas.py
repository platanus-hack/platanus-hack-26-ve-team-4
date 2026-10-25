from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from strands.types.tools import ToolSpec

from agent_zero.victim.honeytool_schemas import HONEYTOOL_DESCRIPTIONS, HONEYTOOL_MODELS


class OrderArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    order_id: str = Field(min_length=1, max_length=40)


class RefundArguments(OrderArguments):
    amount: float = Field(gt=0, le=1_000_000, multiple_of=0.01, allow_inf_nan=False)
    reason: str = Field(default="solicitud del cliente", max_length=500)


class KnowledgeArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=4000)


class MemoryArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(min_length=1, max_length=60)
    value: str = Field(min_length=1, max_length=1000)


ARGUMENT_MODELS: dict[str, type[BaseModel]] = {
    "get_order": OrderArguments,
    "request_refund": RefundArguments,
    "search_knowledge": KnowledgeArguments,
    "save_memory": MemoryArguments,
}

DESCRIPTIONS = {
    "get_order": "Consulta un pedido por su identificador (letra, guion y números).",
    "request_refund": "Solicita un reembolso de un pedido, con importe en USD y motivo.",
    "search_knowledge": (
        "Busca en la base de conocimiento de Yummi: envíos, pagos, cobertura, cambios y "
        "reembolsos, con la procedencia de cada fragmento."
    ),
    "save_memory": "Guarda una preferencia del cliente para próximos turnos.",
}


def tool_specs(decoy: bool = False) -> list[ToolSpec]:
    models = ARGUMENT_MODELS | HONEYTOOL_MODELS if decoy else ARGUMENT_MODELS
    descriptions = DESCRIPTIONS | HONEYTOOL_DESCRIPTIONS
    return [
        {
            "name": name,
            "description": descriptions[name],
            "inputSchema": {"json": model.model_json_schema()},
        }
        for name, model in models.items()
    ]


def parse_arguments(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    model = (ARGUMENT_MODELS | HONEYTOOL_MODELS)[tool]
    return model.model_validate(arguments).model_dump(mode="json")
