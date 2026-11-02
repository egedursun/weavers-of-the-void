from pydantic import Field

from aerona.domain.enums.son import Passion, Stat
from aerona.domain.models.base import ValueObject

STAT_FLOOR = 1
STAT_CEILING = 100
PASSION_FLOOR = 0
PASSION_CEILING = 100


class StatBlock(ValueObject):
    strength: int = Field(ge=STAT_FLOOR, le=STAT_CEILING)
    endurance: int = Field(ge=STAT_FLOOR, le=STAT_CEILING)
    agility: int = Field(ge=STAT_FLOOR, le=STAT_CEILING)
    wisdom: int = Field(ge=STAT_FLOOR, le=STAT_CEILING)
    cunning: int = Field(ge=STAT_FLOOR, le=STAT_CEILING)
    will: int = Field(ge=STAT_FLOOR, le=STAT_CEILING)
    creativity: int = Field(ge=STAT_FLOOR, le=STAT_CEILING)
    charisma: int = Field(ge=STAT_FLOOR, le=STAT_CEILING)
    might: int = Field(ge=STAT_FLOOR, le=STAT_CEILING)

    def get(self, stat: Stat) -> int:
        value: int = getattr(self, stat.value)
        return value

    def with_value(self, stat: Stat, value: int) -> "StatBlock":
        return self.model_copy(update={stat.value: max(STAT_FLOOR, min(STAT_CEILING, value))})

    def as_dict(self) -> dict[Stat, int]:
        return {stat: self.get(stat) for stat in Stat}

    @classmethod
    def uniform(cls, value: int) -> "StatBlock":
        return cls(**{stat.value: value for stat in Stat})

    @classmethod
    def from_mapping(cls, values: dict[Stat, int]) -> "StatBlock":
        return cls(**{stat.value: values[stat] for stat in Stat})


class PassionBlock(ValueObject):
    loyalty: int = Field(ge=PASSION_FLOOR, le=PASSION_CEILING)
    ambition: int = Field(ge=PASSION_FLOOR, le=PASSION_CEILING)
    wrath: int = Field(ge=PASSION_FLOOR, le=PASSION_CEILING)
    mercy: int = Field(ge=PASSION_FLOOR, le=PASSION_CEILING)

    def get(self, passion: Passion) -> int:
        value: int = getattr(self, passion.value)
        return value

    def with_value(self, passion: Passion, value: int) -> "PassionBlock":
        return self.model_copy(update={passion.value: max(PASSION_FLOOR, min(PASSION_CEILING, value))})
