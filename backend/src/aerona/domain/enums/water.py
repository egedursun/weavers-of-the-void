from enum import StrEnum


class SedimentCarrier(StrEnum):
    RIVER = "river"
    WIND = "wind"
    ICE = "ice"
    WAVE = "wave"
    SLOPE = "slope"
    WORKS = "works"


class SedimentKind(StrEnum):
    SILT = "silt"
    SAND = "sand"
    GRAVEL = "gravel"
    VOLCANIC = "volcanic"
    ORGANIC = "organic"
    CLAY = "clay"
    CARBONATE = "carbonate"
    EVAPORITE = "evaporite"
    GLACIAL_FLOUR = "glacial_flour"
    TAILINGS = "tailings"


class CoastForm(StrEnum):
    CLIFF = "cliff"
    BEACH = "beach"
    DELTA = "delta"
    MARSH = "marsh"
    REEF = "reef"
    ICE_SHELF = "ice_shelf"
    FJORD = "fjord"
    LAGOON = "lagoon"
    ESTUARY = "estuary"
    MANGROVE = "mangrove"
    BARRIER_ISLAND = "barrier_island"
    SPIT = "spit"
    ATOLL = "atoll"


class LocalClimateCause(StrEnum):
    VALLEY = "valley"
    SLOPE = "slope"
    WATER_BODY = "water_body"
    FOREST = "forest"
    BUILT_LAND = "built_land"
    WETLAND = "wetland"
    ICE_FIELD = "ice_field"
