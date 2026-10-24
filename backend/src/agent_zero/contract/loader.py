from pathlib import Path

import yaml

from agent_zero.contract.schema import DomainContract


class ContractError(ValueError):
    pass


def parse_contract(text: str) -> DomainContract:
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as failure:
        raise ContractError(f"YAML inválido: {failure}") from failure
    if not isinstance(raw, dict):
        raise ContractError("El contrato debe ser un objeto.")
    try:
        return DomainContract.model_validate(raw)
    except ValueError as failure:
        raise ContractError(str(failure)) from failure


def load_contracts(directory: Path) -> dict[str, DomainContract]:
    contracts: dict[str, DomainContract] = {}
    if not directory.is_dir():
        return contracts
    for path in sorted(directory.glob("*.yaml")):
        contract = parse_contract(path.read_text(encoding="utf-8"))
        if contract.contract_id in contracts:
            raise ContractError(f"Contrato duplicado: {contract.contract_id}.")
        contracts[contract.contract_id] = contract
    return contracts
