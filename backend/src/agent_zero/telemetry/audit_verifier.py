from pydantic import ValidationError

from agent_zero.telemetry.audit_hashing import compute_hash
from agent_zero.telemetry.audit_schemas import GENESIS_HASH, AuditEntry, AuditVerification


def verify_lines(lines: list[str]) -> AuditVerification:
    expected_prev = GENESIS_HASH
    for index, line in enumerate(lines):
        try:
            entry = AuditEntry.model_validate_json(line)
        except ValidationError:
            return _broken(len(lines), index, "Línea ilegible o con formato inválido.")
        if entry.sequence != index:
            return _broken(len(lines), index, "Secuencia fuera de orden.")
        if entry.prev_hash != expected_prev:
            return _broken(len(lines), index, "El hash previo no coincide con la línea anterior.")
        if compute_hash(entry) != entry.hash:
            return _broken(len(lines), index, "El contenido no coincide con su hash.")
        expected_prev = entry.hash
    return AuditVerification(ok=True, entries=len(lines))


def _broken(total: int, index: int, detail: str) -> AuditVerification:
    return AuditVerification(ok=False, entries=total, broken_at=index, detail=detail)
