import base64
import binascii
import hashlib
import hmac
import re

from pydantic import ValidationError

from agent_zero.identity.errors import IdentityDeniedError
from agent_zero.identity.models import IdentityDenialReason
from agent_zero.identity.schemas import AgentPrincipal

_B64URL = re.compile(r"^[A-Za-z0-9_-]+$")


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(text: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    except (binascii.Error, ValueError) as error:
        raise IdentityDeniedError(IdentityDenialReason.MALFORMED) from error


class TokenCodec:
    def __init__(self, signing_key: bytes) -> None:
        self._key = signing_key

    def _sign(self, payload_part: str) -> bytes:
        return hmac.new(self._key, payload_part.encode("ascii"), hashlib.sha256).digest()

    def encode(self, principal: AgentPrincipal) -> str:
        payload_part = _b64encode(principal.model_dump_json().encode("utf-8"))
        return f"{payload_part}.{_b64encode(self._sign(payload_part))}"

    def decode(self, token: str) -> AgentPrincipal:
        parts = token.split(".")
        if len(parts) != 2 or not all(_B64URL.fullmatch(part) for part in parts):
            raise IdentityDeniedError(IdentityDenialReason.MALFORMED)
        payload_part, signature_part = parts
        signature = _b64decode(signature_part)
        if not hmac.compare_digest(signature, self._sign(payload_part)):
            raise IdentityDeniedError(IdentityDenialReason.BAD_SIGNATURE)
        try:
            return AgentPrincipal.model_validate_json(_b64decode(payload_part))
        except ValidationError as error:
            raise IdentityDeniedError(IdentityDenialReason.MALFORMED) from error
