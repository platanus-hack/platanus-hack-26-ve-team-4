from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict

from agent_zero.armor.model_armor import ModelArmor
from agent_zero.memory_bank.memory_erasure_service import MemoryErasureService
from agent_zero.registry.dependencies import OperatorOnly
from agent_zero.shared.dependencies import DbSession
from agent_zero.telemetry.audit_log import AuditLog
from agent_zero.telemetry.audit_schemas import AuditDecision, AuditEvent

router = APIRouter(prefix="/api/memory", tags=["memory"], dependencies=[OperatorOnly])

OPERATOR_ACTOR = "operador"


class ForgetReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    deleted: int


def _audit(request: Request) -> AuditLog:
    audit: AuditLog = request.app.state.audit_log
    return audit


def _armor(request: Request) -> ModelArmor:
    armor: ModelArmor = request.app.state.model_armor
    return armor


@router.post("/subjects/{subject_id}/forget")
async def erase_subject(
    subject_id: str,
    db: DbSession,
    audit: Annotated[AuditLog, Depends(_audit)],
    armor: Annotated[ModelArmor, Depends(_armor)],
) -> ForgetReport:
    deleted = await MemoryErasureService(db).erase_subject(subject_id)
    audit.append(
        AuditEvent(
            actor=OPERATOR_ACTOR,
            action="memory.forget_subject",
            resource=f"subject:{armor.redact_pii(subject_id)[:80]}",
            decision=AuditDecision.ALLOW,
            attributes={"deleted": deleted},
        )
    )
    return ForgetReport(deleted=deleted)
