from enum import StrEnum


class TradePolicyKind(StrEnum):
    TARIFF = "tariff"
    SUBSIDY = "subsidy"
    EMBARGO = "embargo"


class CreditState(StrEnum):
    NORMAL = "normal"
    STRAINED = "strained"
    DEFAULT = "default"
    RESTRUCTURING = "restructuring"


class SpeculationStatus(StrEnum):
    HOARDING = "hoarding"
    SOLD = "sold"
    BUST = "bust"
