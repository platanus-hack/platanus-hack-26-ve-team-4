from agent_zero.identity.models import IdentityDenialReason

_MESSAGES = {
    IdentityDenialReason.MALFORMED: "Credencial malformada.",
    IdentityDenialReason.BAD_SIGNATURE: "La firma de la credencial no es válida.",
    IdentityDenialReason.EXPIRED: "La credencial está vencida.",
    IdentityDenialReason.REVOKED: "La credencial o el agente fue revocado.",
    IdentityDenialReason.MISSING_SCOPE: "La credencial no incluye el permiso solicitado.",
}


class IdentityDeniedError(Exception):
    def __init__(self, reason: IdentityDenialReason) -> None:
        super().__init__(_MESSAGES[reason])
        self.reason = reason
