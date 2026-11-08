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
    PEST_CONTROL = "pest_control"


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


class YieldProduct(StrEnum):
    MEAT = "meat"
    HIDE = "hide"
    BONE = "bone"
    IVORY = "ivory"
    CHITIN = "chitin"
    VENOM = "venom"
    SILK = "silk"
    WOOL = "wool"
    MILK = "milk"
    FEATHERS = "feathers"
    MAGIC_REAGENTS = "magic_reagents"
    DRAGONBONE = "dragonbone"
    EGGS = "eggs"


class FoodLink(StrEnum):
    PINNED = "pinned"
    BARRED = "barred"
    DERIVED = "derived"


class SpeciesClass(StrEnum):
    ANIMAL = "animal"
    PLANT = "plant"
    FUNGUS = "fungus"
    VERMIN = "vermin"


GROWN = frozenset({SpeciesClass.PLANT, SpeciesClass.FUNGUS})


class Biochemistry(StrEnum):
    CARBON_WATER = "carbon_water"
    CARBON_AMMONIA = "carbon_ammonia"
    SILICON = "silicon"
    CRYSTAL = "crystal"
    VOID = "void"
    SPIRIT = "spirit"


UNBOUND_BIOCHEMISTRY = frozenset({Biochemistry.VOID, Biochemistry.SPIRIT})


class GrowthCycle(StrEnum):
    ANNUAL = "annual"
    PERENNIAL = "perennial"
    TREE = "tree"


class Cultivation(StrEnum):
    WILD = "wild"
    GATHERED = "gathered"
    CULTIVATED = "cultivated"
    CULTIVAR = "cultivar"


CULTIVATION_ORDER = tuple(Cultivation)
SOWN = frozenset({Cultivation.CULTIVATED, Cultivation.CULTIVAR})


class PlantYield(StrEnum):
    GRAIN = "grain"
    TUBER = "tuber"
    FIBRE = "fibre"
    DYE = "dye"
    TIMBER = "timber"
    FRUIT = "fruit"
    HERB = "herb"
    BREW_BASE = "brew_base"
    REAGENT = "reagent"
    POISON = "poison"
