from enum import StrEnum


class SedimentCarrier(StrEnum):
    RIVER = "river"
    WIND = "wind"
    ICE = "ice"
    WAVE = "wave"
    SLOPE = "slope"


class SedimentKind(StrEnum):
    SILT = "silt"
    SAND = "sand"
    GRAVEL = "gravel"
    VOLCANIC = "volcanic"
    ORGANIC = "organic"
    CLAY = "clay"
    CARBONATE = "carbonate"
    EVAPORITE = "evaporite"


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


class LocalClimateCause(StrEnum):
    VALLEY = "valley"
    SLOPE = "slope"
    WATER = "water"
    FOREST = "forest"
    BUILT = "built"
