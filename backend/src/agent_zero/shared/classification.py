from enum import StrEnum
from typing import Any


class DataClassification(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

    @property
    def rank(self) -> int:
        return _RANKS[self]

    def covers(self, other: "DataClassification") -> bool:
        return self.rank >= other.rank

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, DataClassification):
            return NotImplemented
        return self.rank < other.rank

    def __le__(self, other: Any) -> bool:
        if not isinstance(other, DataClassification):
            return NotImplemented
        return self.rank <= other.rank

    def __gt__(self, other: Any) -> bool:
        if not isinstance(other, DataClassification):
            return NotImplemented
        return self.rank > other.rank

    def __ge__(self, other: Any) -> bool:
        if not isinstance(other, DataClassification):
            return NotImplemented
        return self.rank >= other.rank


_RANKS = {
    DataClassification.PUBLIC: 0,
    DataClassification.INTERNAL: 1,
    DataClassification.CONFIDENTIAL: 2,
    DataClassification.RESTRICTED: 3,
}
