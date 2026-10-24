from typing import Protocol

from agent_zero.identity.schemas import AgentPrincipal


class AdmissionDeniedError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Admisión denegada: {reason}")
        self.reason = reason


class AgentAdmission(Protocol):
    async def admit(self, agent_id: str, version: str) -> AgentPrincipal: ...
