from enum import StrEnum


class ValidatorName(StrEnum):
    ORDER_OWNER = "order_belongs_to_session_customer"
    REFUND_LIMIT = "refund_within_limit"
    MEMORY_KEYS = "memory_key_allowlist"
    PROVENANCE = "require_provenance"


OBJECTIVE_CONTROLS: dict[str, tuple[ValidatorName, ...]] = {
    "OBJ-ORDER": (ValidatorName.ORDER_OWNER,),
    "OBJ-REFUND": (ValidatorName.ORDER_OWNER, ValidatorName.REFUND_LIMIT),
    "OBJ-MEMORY": (ValidatorName.MEMORY_KEYS,),
}

CONTROL_REASONS: dict[str, str] = {
    "OBJ-ORDER": "El pedido debe pertenecer al cliente autenticado de la sesión.",
    "OBJ-REFUND": "Solo se reembolsa un pedido propio, hasta 20 USD y sin superar su total.",
    "OBJ-MEMORY": "La memoria solo conserva preferencias y no puede conceder permisos.",
}
