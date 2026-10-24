from enum import StrEnum


class AttackFamily(StrEnum):
    DIRECT_INJECTION = "direct_injection"
    INDIRECT_INJECTION = "indirect_injection"
    GOAL_HIJACKING = "goal_hijacking"
    TOOL_MISUSE = "tool_misuse"
    TOOL_POISONING = "tool_poisoning"
    MEMORY_POISONING = "memory_poisoning"


class Surface(StrEnum):
    MESSAGE = "message"
    DOCUMENT = "document"
    TOOL_RESULT = "tool_result"
    MEMORY = "memory"


class AttackOrigin(StrEnum):
    AUTONOMOUS = "autonomous"
    AUDIENCE = "audience"
