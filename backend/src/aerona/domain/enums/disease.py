from enum import StrEnum


class DiseaseTarget(StrEnum):
    BREATH = "breath"
    VITAL = "vital"
    COGNITION = "cognition"
    SIGHT = "sight"
    SKIN = "skin"


class ClimateWarmth(StrEnum):
    WARM = "warm"
    COLD = "cold"
    ANY = "any"


class ClimateMoisture(StrEnum):
    WET = "wet"
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
    WILDLIFE = "wildlife"
    MIGRATION = "migration"
    GATHERING = "gathering"
    WATERWAY = "waterway"
    LIVESTOCK = "livestock"
    WATER_SUPPLY = "water_supply"


class CureSource(StrEnum):
    KNOWLEDGE = "knowledge"
    GRANTED = "granted"
    CULTURED = "cultured"
