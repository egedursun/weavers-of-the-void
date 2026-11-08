from dataclasses import dataclass, field
from enum import StrEnum


class LegacyKind(StrEnum):
    ENTITY = "entity"
    SON = "son"
    CREATOR = "creator"
    FOREIGN_GOD = "foreign_god"
    WORLD = "world"
    STAR = "star"
    CHRONICLE = "chronicle"
    THREAD = "thread"
    ROUTE = "route"
    BOND = "bond"


CREATOR_KEY = 0


@dataclass
class IdMap:
    _ids: dict[tuple[LegacyKind, int], int] = field(default_factory=dict)

    def put(self, kind: LegacyKind, legacy_id: int, new_id: int) -> None:
        self._ids[(kind, legacy_id)] = new_id

    def get(self, kind: LegacyKind, legacy_id: int | None) -> int | None:
        if legacy_id is None:
            return None
        if kind is LegacyKind.CREATOR:
            return self._ids.get((kind, CREATOR_KEY))
        return self._ids.get((kind, legacy_id))

    def has(self, kind: LegacyKind, legacy_id: int | None) -> bool:
        return self.get(kind, legacy_id) is not None

    def creator(self) -> int | None:
        return self._ids.get((LegacyKind.CREATOR, CREATOR_KEY))

    def set_creator(self, new_id: int) -> None:
        self._ids[(LegacyKind.CREATOR, CREATOR_KEY)] = new_id

    def legacy_ids(self, kind: LegacyKind) -> list[int]:
        return sorted(legacy for (stored, legacy) in self._ids if stored is kind)

    def count(self, kind: LegacyKind) -> int:
        return sum(1 for stored, _ in self._ids if stored is kind)

    def reverse(self, kind: LegacyKind) -> dict[int, int]:
        return {new: legacy for (stored, legacy), new in self._ids.items() if stored is kind}

    def reverse_entities(self) -> dict[int, int]:
        return self.reverse(LegacyKind.ENTITY)
