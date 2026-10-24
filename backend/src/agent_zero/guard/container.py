from dataclasses import dataclass

from agent_zero.config import Settings
from agent_zero.contract.loader import load_contracts
from agent_zero.contract.schema import DomainContract
from agent_zero.guard.admin_service import GuardAdminService
from agent_zero.guard.check_service import GuardCheckService
from agent_zero.guard.learning_service import GuardLearningService
from agent_zero.guard.synthesizer import GuardSynthesizer
from agent_zero.llm.gateway import LlmGateway
from agent_zero.shared.database import Database


class UnknownContractError(LookupError):
    pass


@dataclass(frozen=True)
class Guard:
    contracts: dict[str, DomainContract]
    checks: GuardCheckService
    learning: GuardLearningService
    admin: GuardAdminService

    def contract(self, contract_id: str) -> DomainContract:
        found = self.contracts.get(contract_id)
        if found is None:
            raise UnknownContractError(contract_id)
        return found


def build_guard(settings: Settings, database: Database, llm: LlmGateway) -> Guard:
    synthesizer = GuardSynthesizer(llm, settings.llm_mode)
    return Guard(
        contracts=load_contracts(settings.contracts_dir),
        checks=GuardCheckService(database),
        learning=GuardLearningService(database, synthesizer),
        admin=GuardAdminService(database),
    )
