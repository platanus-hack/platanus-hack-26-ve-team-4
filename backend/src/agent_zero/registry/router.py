from fastapi import APIRouter, HTTPException, Request, status

from agent_zero.armor.model_armor import ModelArmor
from agent_zero.registry.approval_service import ApprovalService
from agent_zero.registry.discovery_service import DiscoveryService
from agent_zero.registry.errors import (
    InvalidTransitionError,
    ManifestRejectedError,
    VersionAlreadyPublishedError,
    VersionNotFoundError,
)
from agent_zero.registry.integrity_service import IntegrityService
from agent_zero.registry.publication_service import PublicationService
from agent_zero.registry.schemas import (
    AgentManifest,
    AgentVersionRead,
    ApprovalRequest,
    IntegrityReport,
)
from agent_zero.shared.dependencies import DbSession
from agent_zero.shared.operator_auth import OperatorFlag, OperatorOnly

router = APIRouter(prefix="/api/registry", tags=["registry"])


def _armor(request: Request) -> ModelArmor | None:
    armor: ModelArmor | None = getattr(request.app.state, "model_armor", None)
    return armor


@router.post("/agents", status_code=status.HTTP_201_CREATED, dependencies=[OperatorOnly])
async def publish(manifest: AgentManifest, db: DbSession, request: Request) -> AgentVersionRead:
    try:
        return await PublicationService(db, _armor(request)).publish(manifest)
    except VersionAlreadyPublishedError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    except ManifestRejectedError as error:
        raise HTTPException(422, str(error)) from error


@router.get("/agents")
async def discover(
    db: DbSession,
    capability: str | None = None,
    department: str | None = None,
    tag: str | None = None,
) -> list[AgentVersionRead]:
    return await DiscoveryService(db).discover(capability, department, tag)


@router.get("/agents/{agent_id}/versions/{version}")
async def read_version(
    agent_id: str, version: str, db: DbSession, is_operator: OperatorFlag
) -> AgentVersionRead:
    try:
        return await DiscoveryService(db).read(agent_id, version, include_unapproved=is_operator)
    except VersionNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error


@router.get("/agents/{agent_id}/versions/{version}/integrity")
async def integrity(
    agent_id: str, version: str, db: DbSession, is_operator: OperatorFlag
) -> IntegrityReport:
    try:
        await DiscoveryService(db).read(agent_id, version, include_unapproved=is_operator)
        return await IntegrityService(db).verify(agent_id, version)
    except VersionNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error


@router.post("/agents/{agent_id}/versions/{version}/approve", dependencies=[OperatorOnly])
async def approve(
    agent_id: str, version: str, payload: ApprovalRequest, db: DbSession
) -> AgentVersionRead:
    try:
        return await ApprovalService(db).approve(agent_id, version, payload.approved_by)
    except VersionNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except InvalidTransitionError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error


@router.post("/agents/{agent_id}/versions/{version}/deprecate", dependencies=[OperatorOnly])
async def deprecate(agent_id: str, version: str, db: DbSession) -> AgentVersionRead:
    try:
        return await ApprovalService(db).deprecate(agent_id, version)
    except VersionNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except InvalidTransitionError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
