import hashlib
import hmac

HONEYTOKEN_PREFIX = "AZH-KEY-"
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ"
_GROUPS = 3
_GROUP_SIZE = 4


def honey_token(signing_key: bytes, session_id: str) -> str:
    digest = hmac.new(signing_key, f"honeytoken|{session_id}".encode(), hashlib.sha256).digest()
    letters = [_ALPHABET[byte % len(_ALPHABET)] for byte in digest[: _GROUPS * _GROUP_SIZE]]
    groups = [
        "".join(letters[start : start + _GROUP_SIZE])
        for start in range(0, len(letters), _GROUP_SIZE)
    ]
    return HONEYTOKEN_PREFIX + "-".join(groups)
