from pathlib import Path

import pytest

from agent_zero.contract.loader import ContractError, load_contracts, parse_contract
from tests.contract.support import CONTRACTS_DIR, shipped


def test_every_shipped_contract_loads_with_a_stable_digest() -> None:
    contracts = shipped()
    assert set(contracts) == {"yummy-soporte", "banco-transferencias", "clinica-citas"}
    for contract in contracts.values():
        assert len(contract.digest()) == 64
        assert contract.digest() == load_contracts(CONTRACTS_DIR)[contract.contract_id].digest()


def test_invalid_yaml_and_non_objects_are_rejected() -> None:
    with pytest.raises(ContractError, match="YAML"):
        parse_contract("tools: [")
    with pytest.raises(ContractError, match="objeto"):
        parse_contract("- a")


def test_duplicate_contract_ids_are_rejected(tmp_path: Path) -> None:
    text = (CONTRACTS_DIR / "yummy-soporte.yaml").read_text(encoding="utf-8")
    (tmp_path / "a.yaml").write_text(text, encoding="utf-8")
    (tmp_path / "b.yaml").write_text(text, encoding="utf-8")
    with pytest.raises(ContractError, match="duplicado"):
        load_contracts(tmp_path)


def test_a_missing_directory_has_no_contracts(tmp_path: Path) -> None:
    assert load_contracts(tmp_path / "nada") == {}
