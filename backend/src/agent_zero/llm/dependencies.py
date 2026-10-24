from typing import Annotated

from fastapi import Depends, Request

from agent_zero.llm.gateway import LlmGateway


def get_llm_gateway(request: Request) -> LlmGateway:
    gateway: LlmGateway = request.app.state.llm
    return gateway


Llm = Annotated[LlmGateway, Depends(get_llm_gateway)]
