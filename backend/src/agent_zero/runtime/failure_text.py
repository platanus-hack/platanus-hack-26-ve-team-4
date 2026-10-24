from agent_zero.armor.model_armor import ModelArmor

MAX_FAILURE_LENGTH = 500

_ARMOR = ModelArmor()


def safe_failure_text(text: str) -> str:
    return _ARMOR.redact_pii(text)[:MAX_FAILURE_LENGTH]
