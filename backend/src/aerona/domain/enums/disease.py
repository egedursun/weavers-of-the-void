from enum import StrEnum


class DiseaseVector(StrEnum):
    AIR = "air"
    WATER = "water"
    TOUCH = "touch"
    BITE = "bite"
    SPIRIT = "spirit"
    VOID = "void"
    CURSE = "curse"


class DiseaseTarget(StrEnum):
    BREATH = "breath"
    VITAL = "vital"
    COGNITION = "cognition"
    SIGHT = "sight"
    SKIN = "skin"


class ClimateAffinity(StrEnum):
    WARM = "warm"
    WET = "wet"
    COLD = "cold"
    DRY = "dry"
    ANY = "any"


class OutbreakStatus(StrEnum):
    ACTIVE = "active"
    WANING = "waning"
    ENDED = "ended"


class SpreadPath(StrEnum):
    ORIGIN = "origin"
    ROUTE = "route"
    ARMY = "army"
    JOURNEY = "journey"
    SIEGE = "siege"
    LOOSED = "loosed"
    MUTATION = "mutation"


class CureSource(StrEnum):
    KNOWLEDGE = "knowledge"
    GRANTED = "granted"
