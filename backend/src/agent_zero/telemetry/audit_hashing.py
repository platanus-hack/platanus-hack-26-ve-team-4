import hashlib
import json
from typing import Any

from agent_zero.telemetry.audit_schemas import AuditEntry


def canonical_payload(entry: AuditEntry) -> str:
    body: dict[str, Any] = entry.model_dump(mode="json", exclude={"hash"})
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_hash(entry: AuditEntry) -> str:
    return hashlib.sha256(canonical_payload(entry).encode("utf-8")).hexdigest()
