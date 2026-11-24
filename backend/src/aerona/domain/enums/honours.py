from enum import StrEnum


class UnitHonourKind(StrEnum):
    VICTORY = "victory"
    STAND = "stand"
    SIEGE = "siege"
    SURVIVAL = "survival"
    MASSACRE = "massacre"
    RELIEF = "relief"
    CROSSING = "crossing"
    MERCY = "mercy"
    FIRST_IN = "first_in"


class VeteranGrant(StrEnum):
    LAND = "land"
    PENSION = "pension"
    NONE = "none"
    MEMBERSHIP = "membership"
    TITLE = "title"
    TAX_EXEMPTION = "tax_exemption"
    OFFICE = "office"


class HonourPrivilege(StrEnum):
    PRECEDENCE = "precedence"
    PENSION = "pension"
    LAND = "land"
    SEAT = "seat"
    IMMUNITY = "immunity"
    TITLE = "title"
    NONE = "none"
