from datetime import UTC, datetime

from sqlalchemy import func, select

from agent_zero.arena.transactions import serialize_write
from agent_zero.contract.loader import parse_contract
from agent_zero.contract.schema import DomainContract
from agent_zero.guard.models import GuardContractRecord
from agent_zero.shared.database import Database

MAX_REGISTERED = 100


class UnknownContractError(LookupError):
    pass


class ContractConflictError(ValueError):
    pass


class ContractRegistry:
    def __init__(self, files: dict[str, DomainContract], database: Database) -> None:
        self._files = files
        self._database = database
        self._parsed: dict[str, DomainContract] = {}

    def _parse(self, record: GuardContractRecord) -> DomainContract:
        cached = self._parsed.get(record.digest)
        if cached is None:
            cached = parse_contract(record.source)
            self._parsed[record.digest] = cached
        return cached

    async def get(self, contract_id: str) -> DomainContract:
        found = self._files.get(contract_id)
        if found is not None:
            return found
        async with self._database.sessions() as db:
            record = await db.get(GuardContractRecord, contract_id)
        if record is None:
            raise UnknownContractError(contract_id)
        return self._parse(record)

    async def listed(self) -> list[tuple[DomainContract, str]]:
        async with self._database.sessions() as db:
            records = (
                await db.scalars(
                    select(GuardContractRecord).order_by(GuardContractRecord.contract_id)
                )
            ).all()
        files = [(contract, "file") for contract in self._files.values()]
        return files + [(self._parse(record), "api") for record in records]

    async def register(self, text: str) -> DomainContract:
        contract = parse_contract(text)
        if contract.contract_id in self._files:
            raise ContractConflictError("Ese contrato viene de un archivo del repositorio.")
        async with self._database.sessions() as db:
            await serialize_write(db)
            record = await db.get(GuardContractRecord, contract.contract_id)
            if record is None:
                total = await db.scalar(select(func.count()).select_from(GuardContractRecord))
                if (total or 0) >= MAX_REGISTERED:
                    raise ContractConflictError("Se alcanzó el máximo de contratos registrados.")
                db.add(
                    GuardContractRecord(
                        contract_id=contract.contract_id,
                        version=contract.version,
                        source=text,
                        digest=contract.digest(),
                    )
                )
            else:
                record.version = contract.version
                record.source = text
                record.digest = contract.digest()
                record.updated_at = datetime.now(UTC)
            await db.commit()
        self._parsed[contract.digest()] = contract
        return contract
