from enum import StrEnum


class GroupForm(StrEnum):
    PACK = "pack"
    HERD = "herd"
    COLONY = "colony"
    HIVE = "hive"
    TROOP = "troop"
    FLOCK = "flock"
    SOLITARY_RANGE = "solitary_range"


class DriveMeans(StrEnum):
    HUNT = "hunt"
    FIRE = "fire"
    NOISE = "noise"
    OFFERING = "offering"


class GroupAim(StrEnum):
    RAID = "raid"
    WITHDRAW = "withdraw"
    GUARD = "guard"
    GROW = "grow"
