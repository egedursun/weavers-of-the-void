from aerona.catalog.urban import cargo_class
from aerona.constants.units import PERCENT
from aerona.domain.enums.economy import CommodityKind, TradeMode
from aerona.domain.enums.urban import CargoClass, Preservation
from aerona.rules.registry import Rules

WATER_MODES = frozenset({TradeMode.RIVER, TradeMode.SEA})
LAND_MODES = frozenset({TradeMode.ROAD, TradeMode.CARAVAN})
KEEPING = {Preservation.SALTED: "salted_pct", Preservation.ICED: "iced_pct", Preservation.MAGIC: "magic_pct"}


def carriage_factor(rules: Rules, commodity: CommodityKind, mode: TradeMode) -> float:
    if cargo_class(commodity) is not CargoClass.BULK:
        return 1.0
    if mode in WATER_MODES:
        return rules.cargo.water_bulk_pct / PERCENT
    if mode in LAND_MODES:
        return rules.cargo.land_bulk_pct / PERCENT
    return 1.0


def spoilage(rules: Rules, commodity: CommodityKind, mode: TradeMode, preservation: Preservation) -> float:
    kind = cargo_class(commodity)
    if kind is CargoClass.LIVESTOCK:
        return rules.cargo.livestock_loss / PERCENT
    if kind is not CargoClass.PERISHABLE or mode not in LAND_MODES:
        return 0.0
    key = KEEPING.get(preservation)
    spared = int(getattr(rules.cargo, key)) / PERCENT if key is not None else 0.0
    return rules.cargo.perishable_loss / PERCENT * (1 - spared)
