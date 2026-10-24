import hashlib
import hmac
import json
from typing import Any

from agent_zero.config import Settings
from agent_zero.telemetry.audit_schemas import AuditEntry

KEY_CONTEXT = b"agent-zero/audit-chain"


def canonical_payload(entry: AuditEntry) -> str:
    body: dict[str, Any] = entry.model_dump(mode="json", exclude={"hash"})
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_hash(entry: AuditEntry, key: bytes) -> str:
    return hmac.new(key, canonical_payload(entry).encode("utf-8"), hashlib.sha256).hexdigest()


def derive_audit_key(settings: Settings) -> bytes:
    secret = settings.identity_signing_key.get_secret_value().encode("utf-8")
    return hmac.new(secret, KEY_CONTEXT, hashlib.sha256).digest()
