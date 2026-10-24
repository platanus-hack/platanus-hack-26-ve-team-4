import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from agent_zero.config import Settings
from agent_zero.contract.schema import DomainContract
from agent_zero.fleet.startup_guard import MIN_SECRET_LENGTH
from agent_zero.guard.container import Guard
from agent_zero.guard.contract_registry import UnknownContractError
from agent_zero.memory_bank.memory_cipher import LOCAL_ENVIRONMENTS


def _guard(request: Request) -> Guard:
    guard: Guard = request.app.state.guard
    return guard


def require_guard_key(
    request: Request, x_guard_key: Annotated[str | None, Header()] = None
) -> None:
    settings: Settings = request.app.state.settings
    secret = settings.guard_api_key.get_secret_value()
    if settings.environment not in LOCAL_ENVIRONMENTS and len(secret) < MIN_SECRET_LENGTH:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Guard deshabilitado: falta AGENT_ZERO_GUARD_API_KEY.",
        )
    expected = secret.encode("utf-8")
    if not hmac.compare_digest((x_guard_key or "").encode("utf-8"), expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Clave del Guard inválida.")


async def _contract(contract_id: str, guard: Annotated[Guard, Depends(_guard)]) -> DomainContract:
    try:
        return await guard.registry.get(contract_id)
    except UnknownContractError as failure:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contrato desconocido.") from failure


GuardDep = Annotated[Guard, Depends(_guard)]
ContractDep = Annotated[DomainContract, Depends(_contract)]
GuardKey = Depends(require_guard_key)
