from dataclasses import dataclass

from agent_zero.config import Settings
from agent_zero.contract.loader import load_contracts
from agent_zero.guard.admin_service import GuardAdminService
from agent_zero.guard.check_service import GuardCheckService
from agent_zero.guard.contract_registry import ContractRegistry
from agent_zero.guard.learning_service import GuardLearningService
from agent_zero.guard.synthesizer import GuardSynthesizer
from agent_zero.llm.gateway import LlmGateway
from agent_zero.shared.database import Database


@dataclass(frozen=True)
class Guard:
    registry: ContractRegistry
    checks: GuardCheckService
    learning: GuardLearningService
    admin: GuardAdminService


def build_guard(settings: Settings, database: Database, llm: LlmGateway) -> Guard:
    synthesizer = GuardSynthesizer(llm, settings.llm_mode)
    return Guard(
        registry=ContractRegistry(load_contracts(settings.contracts_dir), database),
        checks=GuardCheckService(database),
        learning=GuardLearningService(database, synthesizer),
        admin=GuardAdminService(database),
    )
