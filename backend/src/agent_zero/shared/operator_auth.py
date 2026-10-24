import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from agent_zero.config import Settings


def _matches(request: Request, provided_secret: str | None) -> bool:
    settings: Settings = request.app.state.settings
    expected = settings.operator_secret.get_secret_value().encode("utf-8")
    return hmac.compare_digest((provided_secret or "").encode("utf-8"), expected)


def require_operator(
    request: Request,
    x_operator_secret: Annotated[str | None, Header()] = None,
) -> None:
    if not _matches(request, x_operator_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Secreto de operador inválido.")


def operator_if_present(
    request: Request,
    x_operator_secret: Annotated[str | None, Header()] = None,
) -> bool:
    if x_operator_secret is None:
        return False
    require_operator(request, x_operator_secret)
    return True


OperatorOnly = Depends(require_operator)
OperatorFlag = Annotated[bool, Depends(operator_if_present)]
