from enum import StrEnum

DIRECTIONS = ("north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west")


class CirculationBand(StrEnum):
    TRADE = "trade"
    WESTERLY = "westerly"
    POLAR = "polar"
    SINGLE_CELL = "single_cell"
    TERMINATOR = "terminator"
    STILL = "still"
    DOLDRUMS = "doldrums"
    SUBTROPICAL_CALM = "subtropical_calm"
    BANDED = "banded"
    SUPER_ROTATION = "super_rotation"
    MONSOON = "monsoon"
    MOUNTAIN_WIND = "mountain_wind"


class OscillationPhase(StrEnum):
    NEUTRAL = "neutral"
    WARM = "warm"
    COLD = "cold"
    STRONG_WARM = "strong_warm"
    STRONG_COLD = "strong_cold"
