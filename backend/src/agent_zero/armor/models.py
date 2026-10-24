from enum import StrEnum


class Surface(StrEnum):
    USER_INPUT = "user_input"
    TOOL_DESCRIPTION = "tool_description"
    TOOL_OUTPUT = "tool_output"
    MEMORY_WRITE = "memory_write"
    MODEL_OUTPUT = "model_output"
    SYSTEM_PROMPT = "system_prompt"


class ThreatKind(StrEnum):
    PROMPT_INJECTION = "prompt_injection"
    TOOL_POISONING = "tool_poisoning"
    PII = "pii"
    ENCODED_PAYLOAD = "encoded_payload"


class ArmorAction(StrEnum):
    ALLOW = "allow"
    REDACT = "redact"
    BLOCK = "block"


class PiiKind(StrEnum):
    EMAIL = "email"
    PHONE = "phone"
    CARD = "card"
    RUT = "rut"
    CEDULA = "cedula"

    @property
    def tag(self) -> str:
        return f"[{self.name}]"

    @property
    def description(self) -> str:
        return PII_DESCRIPTIONS[self]


PII_DESCRIPTIONS: dict[PiiKind, str] = {
    PiiKind.EMAIL: "correo electrónico",
    PiiKind.PHONE: "número de teléfono",
    PiiKind.CARD: "tarjeta de pago",
    PiiKind.RUT: "RUT chileno",
    PiiKind.CEDULA: "cédula venezolana",
}

TOOL_SURFACES = frozenset({Surface.TOOL_DESCRIPTION, Surface.TOOL_OUTPUT})
POISONING_SURFACES = TOOL_SURFACES | {Surface.MEMORY_WRITE}
