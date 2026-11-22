from enum import StrEnum


class EvolvedTrait(StrEnum):
    SIZE = "size"
    SPEED = "speed"
    ARMOUR = "armour"
    VENOM = "venom"
    CAMOUFLAGE = "camouflage"
    COLD_TOLERANCE = "cold_tolerance"
    INTELLIGENCE = "intelligence"
    FECUNDITY = "fecundity"
    WARINESS = "wariness"
    HEAT_TOLERANCE = "heat_tolerance"
    DROUGHT_TOLERANCE = "drought_tolerance"
    KEEN_SENSES = "keen_senses"


class KeystoneRole(StrEnum):
    POLLINATOR = "pollinator"
    SOIL_MAKER = "soil_maker"
    DAM_BUILDER = "dam_builder"
    SCAVENGER = "scavenger"


class PlanetaryCycle(StrEnum):
    CARBON = "carbon"
    WATER = "water"
    NUTRIENTS = "nutrients"


class CycleSource(StrEnum):
    VOLCANOES = "volcanoes"
    FIRES = "fires"
    LIFE = "life"
    FORESTS = "forests"
    OCEANS = "oceans"
    WEATHERING = "weathering"
    MELTING = "melting"
    EVAPORATION = "evaporation"
    FREEZING = "freezing"
    RIVERS = "rivers"
    EROSION = "erosion"


class CycleEffect(StrEnum):
    GREENHOUSE = "greenhouse"
    RAIN = "rain"
    SEA_LEVEL = "sea_level"
    SOIL = "soil"


class TrophicLevel(StrEnum):
    PRODUCER = "producer"
    HERBIVORE = "herbivore"
    CARNIVORE = "carnivore"
    APEX = "apex"


class PlagueResponse(StrEnum):
    CLOSE_BORDERS = "close_borders"
    QUARANTINE = "quarantine"
    BURN_DEAD = "burn_dead"
    EXPEL_SICK = "expel_sick"
    PRAYER = "prayer"
    SEEK_CURE = "seek_cure"


class SuccessionStage(StrEnum):
    BARE = "bare"
    GRASSLAND = "grassland"
    SHRUBLAND = "shrubland"
    YOUNG_FOREST = "young_forest"
    OLD_FOREST = "old_forest"
    MARSH = "marsh"
    SWAMP_FOREST = "swamp_forest"
