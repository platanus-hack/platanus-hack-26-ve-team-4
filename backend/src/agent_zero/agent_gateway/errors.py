from agent_zero.agent_gateway.models import GatewayReason, GatewayStage

_MESSAGES = {
    GatewayReason.IDENTITY_MALFORMED: "la credencial está mal formada",
    GatewayReason.IDENTITY_BAD_SIGNATURE: "la firma de la credencial no es válida",
    GatewayReason.IDENTITY_EXPIRED: "la credencial expiró",
    GatewayReason.IDENTITY_REVOKED: "la credencial fue revocada",
    GatewayReason.IDENTITY_MISSING_SCOPE: "la credencial no incluye el permiso de la herramienta",
    GatewayReason.AGENT_NOT_APPROVED: "la versión del agente no está aprobada en el registro",
    GatewayReason.TOOL_UNREGISTERED: "la herramienta no está registrada en el gateway",
    GatewayReason.TOOL_NOT_IN_MANIFEST: "la herramienta no figura en el manifiesto del agente",
    GatewayReason.CLASSIFICATION_EXCEEDS_CLEARANCE: (
        "la clasificación del dato supera el nivel del agente"
    ),
    GatewayReason.REGION_NOT_ALLOWED_FOR_AGENT: "la región del dato no está permitida al agente",
    GatewayReason.REGION_NOT_ALLOWED_BY_POLICY: "la región del dato incumple la soberanía de datos",
    GatewayReason.RATE_LIMITED: "se superó el límite de llamadas por minuto",
    GatewayReason.INPUT_BLOCKED: "Model Armor bloqueó los argumentos",
    GatewayReason.OUTPUT_BLOCKED: "Model Armor bloqueó la salida de la herramienta",
}


class GatewayDeniedError(Exception):
    def __init__(self, reason: GatewayReason, stage: GatewayStage) -> None:
        detail = _MESSAGES.get(reason, reason.value)
        super().__init__(f"Llamada denegada por el gateway: {detail}.")
        self.reason = reason
        self.stage = stage


class DuplicateToolError(ValueError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Ya existe una herramienta registrada con el nombre {name}.")
        self.name = name


class ToolExecutionError(Exception):
    def __init__(self, original: Exception) -> None:
        super().__init__("La herramienta falló durante su ejecución.")
        self.original = original
