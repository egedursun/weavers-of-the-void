from enum import StrEnum


class ForeignGodStatus(StrEnum):
    AWAKE = "awake"
    ASLEEP = "asleep"
    DEFEATED = "defeated"
    DEAD = "dead"


class ForeignGodPowerEffect(StrEnum):
    SHIELD = "shield"
    CALLER = "caller"
    THIEF = "thief"
    DESTROYER = "destroyer"
    FERTILE = "fertile"
    REVIVING = "reviving"
    DEATHLESS = "deathless"
    SHARP_TONGUED = "sharp_tongued"
