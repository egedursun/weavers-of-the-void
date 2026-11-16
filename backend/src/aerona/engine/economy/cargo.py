from aerona.catalog.urban import CARGO, cargo_class
from aerona.constants.units import PERCENT
from aerona.domain.enums.economy import CommodityKind, TradeMode
from aerona.domain.enums.urban import Preservation
from aerona.rules.registry import Rules

WATER_MODES = frozenset({TradeMode.RIVER, TradeMode.SEA})
LAND_MODES = frozenset({TradeMode.ROAD, TradeMode.CARAVAN})
KEEPING = {Preservation.SALTED: "salted_pct", Preservation.ICED: "iced_pct", Preservation.MAGIC: "magic_pct"}


def carriage_factor(rules: Rules, commodity: CommodityKind, mode: TradeMode) -> float:
    if not CARGO[cargo_class(commodity)].heavy:
        return 1.0
    if mode in WATER_MODES:
        return rules.cargo.water_bulk_pct / PERCENT
    if mode in LAND_MODES:
        return rules.cargo.land_bulk_pct / PERCENT
    return 1.0


def spoilage(rules: Rules, commodity: CommodityKind, mode: TradeMode, preservation: Preservation) -> float:
    spec = CARGO[cargo_class(commodity)]
    if spec.loss_key is None:
        return 0.0
    if not spec.perishes:
        return int(getattr(rules.cargo, spec.loss_key)) / PERCENT
    if mode not in LAND_MODES:
        return 0.0
    key = KEEPING.get(preservation)
    spared = int(getattr(rules.cargo, key)) / PERCENT if key is not None else 0.0
    return rules.cargo.perishable_loss / PERCENT * (1 - spared)
