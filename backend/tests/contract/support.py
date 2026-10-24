from pathlib import Path

from agent_zero.contract.loader import load_contracts
from agent_zero.contract.schema import DomainContract

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "contracts"


def shipped() -> dict[str, DomainContract]:
    return load_contracts(CONTRACTS_DIR)
