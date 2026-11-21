from enum import StrEnum


class ProtectionBasis(StrEnum):
    LAW = "law"
    FAITH = "faith"
    CUSTOM = "custom"
    CHARTER = "charter"
    DIVINE_DECREE = "divine_decree"


class ProtectedUse(StrEnum):
    HUNTING = "hunting"
    LOGGING = "logging"
    FARMING = "farming"
    MINING = "mining"
    SETTLEMENT = "settlement"
    ENTRY = "entry"
    FISHING = "fishing"
    BUILDING = "building"


class ProtectionMeasure(StrEnum):
    HUNTING_BAN = "hunting_ban"
    TRADE_BAN = "trade_ban"
    BREEDING_PROGRAMME = "breeding_programme"
    REINTRODUCTION = "reintroduction"
    HABITAT_GUARD = "habitat_guard"
