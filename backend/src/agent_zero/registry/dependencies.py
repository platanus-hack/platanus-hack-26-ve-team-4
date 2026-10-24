import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from agent_zero.config import Settings


def require_operator(
    request: Request,
    x_operator_secret: Annotated[str | None, Header()] = None,
) -> None:
    settings: Settings = request.app.state.settings
    expected = settings.operator_secret.get_secret_value().encode("utf-8")
    provided = (x_operator_secret or "").encode("utf-8")
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Secreto de operador inválido.")


OperatorOnly = Depends(require_operator)
