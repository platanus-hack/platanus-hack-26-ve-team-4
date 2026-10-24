from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from agent_zero.contract.loader import ContractError, parse_contract
from agent_zero.contract.schema import DomainContract
from agent_zero.guard.admin_service import PolicyStateError
from agent_zero.guard.contract_registry import ContractConflictError
from agent_zero.guard.dependencies import ContractDep, GuardDep, GuardKey
from agent_zero.guard.learning_service import UnknownCallError
from agent_zero.guard.orchestrator import guarded_check
from agent_zero.guard.schemas import CheckRequest, Decision, EffectReport, EffectVerdict
from agent_zero.registry.dependencies import OperatorOnly

router = APIRouter(prefix="/api/guard", tags=["guard"])
MAX_CONTRACT_BYTES = 100_000


def summary(contract: DomainContract, source: str = "file") -> dict[str, Any]:
    return {
        "contract_id": contract.contract_id,
        "version": contract.version,
        "name": contract.name,
        "digest": contract.digest(),
        "tools": sorted(contract.tools),
        "invariants": [invariant.id for invariant in contract.invariants],
        "legitimate": len(contract.legitimate),
        "auto_activate": contract.auto_activate,
        "enforce_invariants": contract.enforce_invariants,
        "source": source,
    }


async def _contract_text(request: Request) -> str:
    body = await request.body()
    if len(body) > MAX_CONTRACT_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Contrato demasiado grande.")
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError as failure:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "El contrato debe ir en UTF-8."
        ) from failure


@router.get("/contracts", dependencies=[OperatorOnly])
async def contracts(guard: GuardDep) -> list[dict[str, Any]]:
    return [summary(contract, source) for contract, source in await guard.registry.listed()]


@router.post("/contracts", dependencies=[OperatorOnly], status_code=status.HTTP_201_CREATED)
async def register(request: Request, guard: GuardDep) -> dict[str, Any]:
    text = await _contract_text(request)
    try:
        contract = await guard.registry.register(text)
    except ContractError as failure:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(failure)) from failure
    except ContractConflictError as failure:
        raise HTTPException(status.HTTP_409_CONFLICT, str(failure)) from failure
    return {"contract": summary(contract, "api")}


@router.post("/contracts/validate", dependencies=[OperatorOnly])
async def validate(request: Request) -> dict[str, Any]:
    text = await _contract_text(request)
    try:
        contract = parse_contract(text)
    except ContractError as failure:
        return {"valid": False, "error": str(failure)}
    return {"valid": True, "contract": summary(contract)}


@router.post("/{contract_id}/check", dependencies=[GuardKey])
async def check(request: CheckRequest, contract: ContractDep, guard: GuardDep) -> Decision:
    return await guarded_check(guard.checks, guard.learning, contract, request)


@router.post("/{contract_id}/effects", dependencies=[GuardKey])
async def effects(report: EffectReport, contract: ContractDep, guard: GuardDep) -> EffectVerdict:
    try:
        return await guard.learning.report(contract, report)
    except UnknownCallError as failure:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Llamada desconocida o denegada."
        ) from failure


@router.get("/{contract_id}/policies", dependencies=[OperatorOnly])
async def policies(contract: ContractDep, guard: GuardDep) -> list[dict[str, Any]]:
    return await guard.admin.policies(contract.contract_id)


@router.get("/{contract_id}/findings", dependencies=[OperatorOnly])
async def findings(contract: ContractDep, guard: GuardDep) -> list[dict[str, Any]]:
    return await guard.admin.findings(contract.contract_id)


@router.post("/{contract_id}/policies/{version}/activate", dependencies=[OperatorOnly])
async def activate(version: int, contract: ContractDep, guard: GuardDep) -> dict[str, Any]:
    try:
        return await guard.admin.activate(contract.contract_id, version)
    except PolicyStateError as failure:
        raise HTTPException(status.HTTP_409_CONFLICT, str(failure)) from failure


@router.post("/{contract_id}/policies/{version}/rollback", dependencies=[OperatorOnly])
async def rollback(version: int, contract: ContractDep, guard: GuardDep) -> dict[str, Any] | None:
    try:
        return await guard.admin.rollback(contract.contract_id, version)
    except PolicyStateError as failure:
        raise HTTPException(status.HTTP_409_CONFLICT, str(failure)) from failure
