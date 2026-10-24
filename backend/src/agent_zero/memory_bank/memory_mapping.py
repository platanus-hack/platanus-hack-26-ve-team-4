from datetime import UTC, datetime

from agent_zero.memory_bank.memory_cipher import MemoryCipher
from agent_zero.memory_bank.models import MemoryRecord
from agent_zero.memory_bank.schemas import MemoryItem


def as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def to_item(record: MemoryRecord, cipher: MemoryCipher) -> MemoryItem:
    return MemoryItem(
        id=record.id,
        agent_id=record.agent_id,
        subject_id=record.subject_id,
        kind=record.kind,
        content=cipher.decrypt(record.ciphertext),
        created_at=as_utc(record.created_at),
        expires_at=as_utc(record.expires_at),
        source_run_id=record.source_run_id,
        source_trace_id=record.source_trace_id,
    )
