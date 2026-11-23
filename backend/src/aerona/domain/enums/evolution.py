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
    DISEASE_RESISTANCE = "disease_resistance"
    DOCILITY = "docility"
    LONGEVITY = "longevity"


class KeystoneRole(StrEnum):
    POLLINATOR = "pollinator"
    SOIL_MAKER = "soil_maker"
    DAM_BUILDER = "dam_builder"
    SCAVENGER = "scavenger"
    SEED_DISPERSER = "seed_disperser"
    REGULATOR = "regulator"
    REEF_BUILDER = "reef_builder"


class PlanetaryCycle(StrEnum):
    CARBON = "carbon"
    WATER = "water"
    NUTRIENTS = "nutrients"
    OXYGEN = "oxygen"
    ROCK = "rock"


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
    INDUSTRY = "industry"
    UPLIFT = "uplift"
    BURIAL = "burial"


class CycleEffect(StrEnum):
    GREENHOUSE = "greenhouse"
    RAIN = "rain"
    SEA_LEVEL = "sea_level"
    SOIL = "soil"
    BREATH = "breath"


class TrophicLevel(StrEnum):
    PRODUCER = "producer"
    HERBIVORE = "herbivore"
    CARNIVORE = "carnivore"
    APEX = "apex"
    DECOMPOSER = "decomposer"


class PlagueResponse(StrEnum):
    CLOSE_BORDERS = "close_borders"
    QUARANTINE = "quarantine"
    BURN_DEAD = "burn_dead"
    EXPEL_SICK = "expel_sick"
    PRAYER = "prayer"
    SEEK_CURE = "seek_cure"
    SANITATION = "sanitation"


class SuccessionStage(StrEnum):
    BARE = "bare"
    GRASSLAND = "grassland"
    SHRUBLAND = "shrubland"
    YOUNG_FOREST = "young_forest"
    OLD_FOREST = "old_forest"
    MARSH = "marsh"
    SWAMP_FOREST = "swamp_forest"
    PIONEER = "pioneer"
    OPEN_WATER = "open_water"
    BOG = "bog"
    HEATH = "heath"
    COASTAL_DUNE = "coastal_dune"
