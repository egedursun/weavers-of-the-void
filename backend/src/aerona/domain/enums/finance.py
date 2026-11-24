from enum import StrEnum


class TradePolicyKind(StrEnum):
    TARIFF = "tariff"
    SUBSIDY = "subsidy"
    EMBARGO = "embargo"
    QUOTA = "quota"
    LICENCE = "licence"
    PRICE_CONTROL = "price_control"
    FREE_TRADE = "free_trade"
    EXPORT_BAN = "export_ban"
    SANCTION = "sanction"
    TOLL = "toll"
    STAPLE_RIGHT = "staple_right"


class CreditState(StrEnum):
    NORMAL = "normal"
    STRAINED = "strained"
    DEFAULT = "default"
    RESTRUCTURING = "restructuring"
    RESCUED = "rescued"
    REPUDIATED = "repudiated"
    FROZEN = "frozen"


class SpeculationStatus(StrEnum):
    HOARDING = "hoarding"
    SOLD = "sold"
    BUST = "bust"
    SEIZED = "seized"
    SPOILED = "spoiled"
