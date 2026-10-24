from pydantic import ValidationError

from agent_zero.telemetry.audit_anchor import AnchorStore, anchor_matches
from agent_zero.telemetry.audit_hashing import compute_hash
from agent_zero.telemetry.audit_schemas import GENESIS_HASH, AuditEntry, AuditVerification

ANCHOR_MISMATCH = (
    "El ancla firmada no coincide con el final del archivo: hay líneas "
    "truncadas, añadidas o reescritas sin la clave."
)


def _line_problem(line: str, index: int, expected_prev: str, key: bytes) -> str | None:
    try:
        entry = AuditEntry.model_validate_json(line)
    except ValidationError:
        return "Línea ilegible o con formato inválido."
    if entry.sequence != index:
        return "Secuencia fuera de orden."
    if entry.prev_hash != expected_prev:
        return "El hash previo no coincide con la línea anterior."
    if compute_hash(entry, key) != entry.hash:
        return "El contenido no coincide con su firma."
    return None


def verify_lines(lines: list[str], key: bytes, anchor: AnchorStore) -> AuditVerification:
    expected_prev = GENESIS_HASH
    for index, line in enumerate(lines):
        problem = _line_problem(line, index, expected_prev, key)
        if problem is not None:
            return _broken(len(lines), index, problem)
        expected_prev = AuditEntry.model_validate_json(line).hash
    raw = anchor.read()
    if not lines and raw is None:
        return AuditVerification(ok=True, entries=0)
    if not anchor_matches(key, raw, len(lines), expected_prev):
        return _broken(len(lines), len(lines), ANCHOR_MISMATCH)
    return AuditVerification(ok=True, entries=len(lines))


def _broken(total: int, index: int, detail: str) -> AuditVerification:
    return AuditVerification(ok=False, entries=total, broken_at=index, detail=detail)
