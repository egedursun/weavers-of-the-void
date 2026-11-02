from enum import StrEnum

from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import has_stat, headcount_key, set_stats, stat, stat_or
from aerona.rules.registry import Rules


class Trait(StrEnum):
    POPULATION = "population"
    FOLLOWERS = "followers"
    PIETY = "piety"
    PROSPERITY = "prosperity"
    WEALTH = "wealth"
    CRAFT = "craft"
    DEFENSE = "defense"
    STRENGTH = "strength"
    AGILITY = "agility"
    INTELLECT = "intellect"
    CHARISMA = "charisma"
    SWAY = "sway"
    INFLUENCE = "influence"
    ZEAL = "zeal"
    DEVOTION = "devotion"
    HP = "hp"
    AGE = "age"
    LIFESPAN = "lifespan"
    ABUNDANCE = "abundance"
    FERTILITY = "fertility"
    DANGER = "danger"
    MARTIALITY = "martiality"
    PROTECTION = "protection"
    UNREST = "unrest"


OPEN_ENDED_TRAITS = frozenset({Trait.POPULATION, Trait.FOLLOWERS, Trait.DEVOTION, Trait.HP, Trait.AGE, Trait.LIFESPAN})


def has_trait(entity: EntityRow, trait_key: Trait) -> bool:
    return has_stat(entity, trait_key.value)


def trait(entity: EntityRow, trait_key: Trait) -> int | None:
    return stat(entity, trait_key.value)


def trait_or(entity: EntityRow, trait_key: Trait, default: int) -> int:
    return stat_or(entity, trait_key.value, default)


def set_trait(entity: EntityRow, trait_key: Trait, value: float) -> bool:
    if not has_trait(entity, trait_key):
        return False
    number = max(PERCENT_MIN, round_half_up(value)) if trait_key in OPEN_ENDED_TRAITS else clamp_int(value, PERCENT_MIN, PERCENT_MAX)
    set_stats(entity, **{trait_key.value: number})
    return True


def add_trait(entity: EntityRow, trait_key: Trait, delta: float) -> bool:
    current = trait(entity, trait_key)
    if current is None:
        return False
    return set_trait(entity, trait_key, current + delta)


def headcount_trait(entity: EntityRow) -> Trait | None:
    key = Trait(headcount_key(entity))
    return key if trait(entity, key) is not None else None


def headcount_floor(rules: Rules, trait_key: Trait) -> int:
    return 1 if trait_key is Trait.FOLLOWERS else rules.limits.population_floor
