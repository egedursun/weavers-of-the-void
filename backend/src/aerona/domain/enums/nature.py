from enum import StrEnum


class FermentKind(StrEnum):
    YEAST = "yeast"
    STARTER = "starter"
    MOULD = "mould"
    LACTIC = "lactic"
    VINEGAR = "vinegar"
    ALKALINE = "alkaline"
    WILD = "wild"


class SymbiosisKind(StrEnum):
    MUTUALISM = "mutualism"
    COMMENSALISM = "commensalism"
    PARASITISM = "parasitism"
    MIMICRY = "mimicry"
    AMENSALISM = "amensalism"
    FARMING = "farming"


class Dormancy(StrEnum):
    NONE = "none"
    HIBERNATION = "hibernation"
    AESTIVATION = "aestivation"
    TORPOR = "torpor"
    CRYPTOBIOSIS = "cryptobiosis"
    DIAPAUSE = "diapause"


class Thermoregulation(StrEnum):
    ENDOTHERM = "endotherm"
    ECTOTHERM = "ectotherm"
    HETEROTHERM = "heterotherm"
    ATHERMIC = "athermic"
    MESOTHERM = "mesotherm"


class SenseKind(StrEnum):
    SIGHT = "sight"
    NIGHT_VISION = "night_vision"
    SMELL = "smell"
    HEARING = "hearing"
    ECHOLOCATION = "echolocation"
    VIBRATION = "vibration"
    MAGNETIC = "magnetic"
    SPIRIT_SIGHT = "spirit_sight"
    HEAT = "heat"
    ELECTRIC = "electric"
    ULTRAVIOLET = "ultraviolet"
    TASTE = "taste"
    PRESSURE = "pressure"


class SenseCause(StrEnum):
    BASE = "base"
    NOCTURNAL = "nocturnal"
    FLESH_SEEKER = "flesh_seeker"
    PLANT_EATER = "plant_eater"
    ECHOLOCATION = "echolocation"
    BURROWING = "burrowing"
    MIGRATORY = "migratory"
    SPIRIT_SIGHT = "spirit_sight"
    COLD_HUNTER = "cold_hunter"
    WATER_HUNTER = "water_hunter"
    FLOWER_SEEKER = "flower_seeker"


class PlantDefence(StrEnum):
    NONE = "none"
    THORNS = "thorns"
    TOXINS = "toxins"
    ALLELOPATHY = "allelopathy"
    CARNIVOROUS = "carnivorous"
    STINGING = "stinging"
    GUARDIANS = "guardians"
    MIMICRY = "mimicry"
    REGROWTH = "regrowth"
