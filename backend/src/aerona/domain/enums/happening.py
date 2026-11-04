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


class RiverShiftCause(StrEnum):
    FLOOD = "flood"
    QUAKE = "quake"
    DIVINE = "divine"
    PLAYER = "player"
