from enum import StrEnum


class FermentKind(StrEnum):
    YEAST = "yeast"
    STARTER = "starter"
    MOULD = "mould"
    LACTIC = "lactic"
    VINEGAR = "vinegar"


class SymbiosisKind(StrEnum):
    MUTUALISM = "mutualism"
    COMMENSALISM = "commensalism"
    PARASITISM = "parasitism"
    MIMICRY = "mimicry"


class Dormancy(StrEnum):
    NONE = "none"
    HIBERNATION = "hibernation"
    AESTIVATION = "aestivation"


class Thermoregulation(StrEnum):
    ENDOTHERM = "endotherm"
    ECTOTHERM = "ectotherm"


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


class PlantDefence(StrEnum):
    NONE = "none"
    THORNS = "thorns"
    TOXINS = "toxins"
    ALLELOPATHY = "allelopathy"
    CARNIVOROUS = "carnivorous"
