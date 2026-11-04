from enum import StrEnum


class SizeClass(StrEnum):
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    HUGE = "huge"
    COLOSSAL = "colossal"


SIZE_ORDER = tuple(SizeClass)


class Diet(StrEnum):
    HERBIVORE = "herbivore"
    CARNIVORE = "carnivore"
    OMNIVORE = "omnivore"
    SCAVENGER = "scavenger"
    FILTER = "filter"
    PHOTOSYNTHETIC = "photosynthetic"
    MINERAL = "mineral"
    SOUL = "soul"
    VOID = "void"


HUNTERS = frozenset({Diet.CARNIVORE, Diet.OMNIVORE, Diet.SOUL})
GRAZERS = frozenset({Diet.HERBIVORE, Diet.OMNIVORE, Diet.FILTER})


class Sociality(StrEnum):
    SOLITARY = "solitary"
    PACK = "pack"
    HERD = "herd"
    HIVE = "hive"


class DomesticationStage(StrEnum):
    WILD = "wild"
    TAMED = "tamed"
    HERDED = "herded"
    DOMESTICATED = "domesticated"
    BREED = "breed"


STAGE_ORDER = tuple(DomesticationStage)


class SpeciesUse(StrEnum):
    FOOD = "food"
    LABOUR = "labour"
    MOUNT = "mount"
    WAR = "war"
    GUARD = "guard"
    COMPANION = "companion"
    SACRIFICE = "sacrifice"
    MAGIC = "magic"


class RangeTrend(StrEnum):
    RISING = "rising"
    STEADY = "steady"
    FALLING = "falling"


class BeastTemper(StrEnum):
    HUNGRY = "hungry"
    TERRITORIAL = "territorial"
    SLEEPING = "sleeping"
    ENRAGED = "enraged"
    BOUND = "bound"
    TAMED = "tamed"
