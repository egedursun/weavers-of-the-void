from enum import StrEnum


class EventPhase(StrEnum):
    ONSET = "onset"
    PEAK = "peak"
    AFTERMATH = "aftermath"


class LandAct(StrEnum):
    SHIFT_RIVER = "shift_river"
    PARCH = "parch"
    GREEN = "green"
    SALT_SOIL = "salt_soil"
    ENRICH_SOIL = "enrich_soil"
    RAISE_LAND = "raise_land"
    LOWER_LAND = "lower_land"
    CARVE_VALLEY = "carve_valley"
    FILL_VALLEY = "fill_valley"
    OPEN_SPRING = "open_spring"
    CALL_LAVA = "call_lava"
    SINK_COAST = "sink_coast"


class RiverShiftCause(StrEnum):
    FLOOD = "flood"
    QUAKE = "quake"
    DIVINE = "divine"
    PLAYER = "player"
