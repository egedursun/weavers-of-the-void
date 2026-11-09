from enum import StrEnum


class LifeComplexity(StrEnum):
    NONE = "none"
    MICROBIAL = "microbial"
    SIMPLE = "simple"
    COMPLEX = "complex"
    SAPIENT = "sapient"


class LifeEnvironment(StrEnum):
    MARINE = "marine"
    TERRESTRIAL = "terrestrial"
    AERIAL = "aerial"
    SUBTERRANEAN = "subterranean"


class AirNeed(StrEnum):
    OXYGEN = "oxygen"
    CARBON_DIOXIDE = "carbon_dioxide"
    METHANE = "methane"
    NONE = "none"


class CosmicFeatureKind(StrEnum):
    ASTEROID_FIELD = "asteroid_field"
    WORMHOLE = "wormhole"
    PERIODIC_COMET = "periodic_comet"
    ROGUE_WORLD = "rogue_world"
    GRAVITY_WELL = "gravity_well"


class SurveyLevel(StrEnum):
    UNKNOWN = "unknown"
    RUMOURED = "rumoured"
    DETECTED = "detected"
    OBSERVED = "observed"
    SURVEYED = "surveyed"
    MAPPED = "mapped"


SURVEY_ORDER: tuple[SurveyLevel, ...] = tuple(SurveyLevel)


class SystemRole(StrEnum):
    PRIMARY = "primary"
    COMPANION = "companion"


class ImpactBody(StrEnum):
    ASTEROID = "asteroid"
    COMET = "comet"
    ROGUE_WORLD = "rogue_world"
    CALLED = "called"


class ImpactOutcome(StrEnum):
    PENDING = "pending"
    STRUCK = "struck"
    DEFLECTED = "deflected"
    MISSED = "missed"


class TerraformAim(StrEnum):
    THICKEN_AIR = "thicken_air"
    THIN_AIR = "thin_air"
    BREATHABLE_AIR = "breathable_air"
    WARM = "warm"
    COOL = "cool"
    WATER = "water"
    DRY = "dry"
    BRIGHTEN = "brighten"
    DARKEN = "darken"
