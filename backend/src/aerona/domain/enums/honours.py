from enum import StrEnum


class UnitHonourKind(StrEnum):
    VICTORY = "victory"
    STAND = "stand"
    SIEGE = "siege"
    SURVIVAL = "survival"
    MASSACRE = "massacre"


class VeteranGrant(StrEnum):
    LAND = "land"
    PENSION = "pension"
    NONE = "none"


class HonourPrivilege(StrEnum):
    PRECEDENCE = "precedence"
    PENSION = "pension"
    LAND = "land"
    SEAT = "seat"
    IMMUNITY = "immunity"
    TITLE = "title"
    NONE = "none"
