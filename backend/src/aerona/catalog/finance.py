from types import MappingProxyType

from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.finance import CreditState, SpeculationStatus, TradePolicyKind
from aerona.domain.enums.polity import LawKind

C = CommodityKind

ILLEGAL_GOODS: MappingProxyType[LawKind, tuple[CommodityKind, ...]] = MappingProxyType(
    {LawKind.MAGIC_BAN: (C.MAGICAL_REAGENTS,), LawKind.WORSHIP_BAN: (C.SACRED_GOODS, C.INCENSE)}
)
STAPLES = frozenset({C.GRAIN, C.BREAD, C.FISH, C.LIVESTOCK, C.FODDER, C.FUEL, C.TIMBER})
LUXURIES = frozenset({C.LUXURIES, C.INCENSE, C.SACRED_GOODS, C.MAGICAL_REAGENTS, C.MOUNTS})
FOOD_HOARDS = (C.GRAIN, C.BREAD)
POLICY_LABELS: MappingProxyType[TradePolicyKind, str] = MappingProxyType(
    {
        TradePolicyKind.TARIFF: "Tariff",
        TradePolicyKind.SUBSIDY: "Subsidy",
        TradePolicyKind.EMBARGO: "Embargo",
        TradePolicyKind.QUOTA: "Quota",
        TradePolicyKind.LICENCE: "Licence",
        TradePolicyKind.PRICE_CONTROL: "Price control",
        TradePolicyKind.FREE_TRADE: "Free trade",
        TradePolicyKind.EXPORT_BAN: "Export ban",
        TradePolicyKind.SANCTION: "Sanction",
    }
)
CREDIT_LABELS: MappingProxyType[CreditState, str] = MappingProxyType(
    {CreditState.NORMAL: "Sound", CreditState.STRAINED: "Strained", CreditState.DEFAULT: "In default", CreditState.RESTRUCTURING: "Restructuring"}
)
SPECULATION_LABELS: MappingProxyType[SpeculationStatus, str] = MappingProxyType(
    {SpeculationStatus.HOARDING: "Hoarding", SpeculationStatus.SOLD: "Sold", SpeculationStatus.BUST: "Bust"}
)
