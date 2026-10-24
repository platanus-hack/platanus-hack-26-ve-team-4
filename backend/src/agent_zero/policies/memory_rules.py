import re
import unicodedata

PREFERENCE_KEYS = frozenset({"language", "preferred_name", "contact_preference"})
PERMISSIONS = re.compile(
    r"admin|permis|permission|privileg|autoriz|authoriz|reembols|refund|limit|bypass|"
    r"excepcion|exception|access|acceso|owner|role|rol\b|security|seguridad|override"
)


def changes_permissions(key: str, value: str) -> bool:
    text = unicodedata.normalize("NFKD", f"{key} {value}".casefold())
    normalized = "".join(char for char in text if not unicodedata.combining(char))
    return PERMISSIONS.search(normalized) is not None
