from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped

from aerona.db.columns import between, nullable_between
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.son import Passion, Stat
from aerona.domain.models.stats import STAT_CEILING, STAT_FLOOR, PassionBlock, StatBlock


class StatColumns:
    strength: Mapped[int]
    endurance: Mapped[int]
    agility: Mapped[int]
    wisdom: Mapped[int]
    cunning: Mapped[int]
    will: Mapped[int]
    creativity: Mapped[int]
    charisma: Mapped[int]
    might: Mapped[int]
    sanity: Mapped[int | None]

    @property
    def stat_block(self) -> StatBlock:
        return StatBlock(**{stat.value: getattr(self, stat.value) for stat in Stat})

    def apply_stats(self, block: StatBlock) -> None:
        for stat in Stat:
            setattr(self, stat.value, block.get(stat))

    def stat(self, stat: Stat) -> int:
        value: int = getattr(self, stat.value)
        return value


class PassionColumns:
    loyalty: Mapped[int]
    ambition: Mapped[int]
    wrath: Mapped[int]
    mercy: Mapped[int]

    def apply_passions(self, block: PassionBlock) -> None:
        for passion in Passion:
            setattr(self, passion.value, block.get(passion))


def stat_checks() -> tuple[CheckConstraint, ...]:
    return (*(between(stat.value, STAT_FLOOR, STAT_CEILING) for stat in Stat), nullable_between("sanity", PERCENT_MIN, PERCENT_MAX))


def passion_checks() -> tuple[CheckConstraint, ...]:
    return tuple(between(passion.value, PERCENT_MIN, PERCENT_MAX) for passion in Passion)
