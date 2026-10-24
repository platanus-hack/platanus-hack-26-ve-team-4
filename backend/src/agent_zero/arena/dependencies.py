from typing import Annotated

from fastapi import Depends, Request

from agent_zero.arena.core import ProductCore


def get_core(request: Request) -> ProductCore:
    core: ProductCore = request.app.state.core
    return core


Core = Annotated[ProductCore, Depends(get_core)]
