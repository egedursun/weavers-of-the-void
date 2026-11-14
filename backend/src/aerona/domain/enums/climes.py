from enum import StrEnum

DIRECTIONS = ("north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west")


class CirculationBand(StrEnum):
    TRADE = "trade"
    WESTERLY = "westerly"
    POLAR = "polar"
    SINGLE_CELL = "single_cell"
    TERMINATOR = "terminator"
    STILL = "still"


class OscillationPhase(StrEnum):
    NEUTRAL = "neutral"
    WARM = "warm"
    COLD = "cold"
