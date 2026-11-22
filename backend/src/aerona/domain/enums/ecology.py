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
    PISCIVORE = "piscivore"
    SANGUIVORE = "sanguivore"


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


class AnimalRole(StrEnum):
    DRAFT = "draft"
    MOUNT = "mount"
    DAIRY = "dairy"
    FIBRE = "fibre"
    MEAT = "meat"
    GUARD = "guard"
    HUNTING = "hunting"
    WAR = "war"
    COMPANION = "companion"
    SACRED = "sacred"
    PEST_CONTROL = "pest_control"
    MESSENGER = "messenger"
    SENSING = "sensing"
    ENTERTAINMENT = "entertainment"
    REAGENT_SOURCE = "reagent_source"


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
    COMPANION = "companion"


class YieldProduct(StrEnum):
    MEAT = "meat"
    HIDE = "hide"
    CALCIFIED_TISSUE = "calcified_tissue"
    IVORY = "ivory"
    CHITIN = "chitin"
    VENOM = "venom"
    SILK = "silk"
    WOOL = "wool"
    MILK = "milk"
    FEATHERS = "feathers"
    MAGIC_REAGENTS = "magic_reagents"
    GREAT_BEAST_TISSUE = "great_beast_tissue"
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
    MICROBE = "microbe"
    MINERAL = "mineral"
    GASEOUS = "gaseous"
    ENERGY = "energy"
    MADE = "made"
    COLONIAL = "colonial"
    HYBRID = "hybrid"


class Biochemistry(StrEnum):
    CARBON_WATER = "carbon_water"
    CARBON_AMMONIA = "carbon_ammonia"
    SILICON = "silicon"
    CRYSTAL = "crystal"
    VOID = "void"
    SPIRIT = "spirit"


class GrowthCycle(StrEnum):
    ANNUAL = "annual"
    PERENNIAL = "perennial"
    TREE = "tree"


class Cultivation(StrEnum):
    WILD = "wild"
    GATHERED = "gathered"
    CULTIVATED = "cultivated"
    CULTIVAR = "cultivar"


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


class HerdTraining(StrEnum):
    WAR = "war"
    HUNTING = "hunting"
    GUARD = "guard"


class TissueMaterial(StrEnum):
    SOFT_TISSUE = "soft_tissue"
    HIDE = "hide"
    PLATES = "plates"
    SHELL = "shell"
    PLUMAGE = "plumage"
    RIGID = "rigid"
    FIBROUS = "fibrous"
    FROZEN = "frozen"
    VAPOUR = "vapour"
    MINERAL = "mineral"
    METALLIC = "metallic"
    CRYSTALLINE = "crystalline"
    GEL = "gel"
    ENERGY = "energy"
    INSUBSTANTIAL = "insubstantial"


class AttackDelivery(StrEnum):
    BREATH = "breath"
    SPIT = "spit"
    SPRAY = "spray"
    EMANATION = "emanation"
    GAZE = "gaze"
    VOICE = "voice"
    TOUCH = "touch"
    SPORES = "spores"
    BITE = "bite"
    STING = "sting"


class AttackEffect(StrEnum):
    HEAT = "heat"
    COLD = "cold"
    CORROSION = "corrosion"
    SHOCK = "shock"
    VENOM = "venom"
    FORCE = "force"
    ENTANGLE = "entangle"
    FEAR = "fear"
    STILLNESS = "stillness"
    SLEEP = "sleep"
    CONFUSION = "confusion"
    CHARM = "charm"
    DRAIN = "drain"


class AttackRange(StrEnum):
    TOUCH = "touch"
    NEAR = "near"
    FAR = "far"
    SIGHT = "sight"


class Temperament(StrEnum):
    PLACID = "placid"
    SKITTISH = "skittish"
    CURIOUS = "curious"
    FIERCE = "fierce"
    CUNNING = "cunning"
    SEIZES_PREY = "seizes_prey"


class Aversion(StrEnum):
    FIRE = "fire"
    IRON = "iron"
    NOISE = "noise"
    WATER = "water"
    HOLY_GROUND = "holy_ground"


class AwakeningTrigger(StrEnum):
    DEEP_MINING = "deep_mining"
    DESECRATION = "desecration"


class Habitat(StrEnum):
    LAND = "land"
    WATER = "water"
    SKY = "sky"
    DEEP = "deep"
    VOID = "void"
