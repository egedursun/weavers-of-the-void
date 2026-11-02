from enum import StrEnum


class Rarity(StrEnum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"

    @property
    def rank(self) -> int:
        return RARITY_ORDER.index(self)

    def at_least(self, minimum: "Rarity") -> bool:
        return self.rank >= minimum.rank

    def next(self) -> "Rarity | None":
        position = self.rank + 1
        return RARITY_ORDER[position] if position < len(RARITY_ORDER) else None

    @classmethod
    def from_rank(cls, rank: int) -> "Rarity":
        return RARITY_ORDER[max(0, min(len(RARITY_ORDER) - 1, rank))]


RARITY_ORDER: tuple[Rarity, ...] = (
    Rarity.COMMON,
    Rarity.UNCOMMON,
    Rarity.RARE,
    Rarity.EPIC,
    Rarity.LEGENDARY,
    Rarity.MYTHIC,
)
