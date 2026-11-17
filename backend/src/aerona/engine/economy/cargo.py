from aerona.catalog.preservation import PRESERVATION
from aerona.catalog.urban import CARGO
from aerona.constants.units import PERCENT
from aerona.domain.enums.economy import TradeMode
from aerona.domain.enums.urban import CargoClass, PreservationMethod
from aerona.rules.registry import Rules

WATER_MODES = frozenset({TradeMode.RIVER, TradeMode.SEA})
LAND_MODES = frozenset({TradeMode.ROAD, TradeMode.CARAVAN})


def carriage_factor(rules: Rules, cargo: CargoClass, mode: TradeMode, bulk: float = 1.0) -> float:
    if not CARGO[cargo].heavy:
        return 1.0
    if mode in WATER_MODES:
        return rules.cargo.water_bulk_pct / PERCENT * bulk
    if mode in LAND_MODES:
        return rules.cargo.land_bulk_pct / PERCENT * bulk
    return 1.0


def spoilage(rules: Rules, cargo: CargoClass, mode: TradeMode, preservation: PreservationMethod) -> float:
    spec = CARGO[cargo]
    if spec.loss_key is None:
        return 0.0
    if not spec.perishes:
        return int(getattr(rules.cargo, spec.loss_key)) / PERCENT
    if mode not in LAND_MODES:
        return 0.0
    spared = PRESERVATION[preservation].keeping(rules) / PERCENT
    return rules.cargo.perishable_loss / PERCENT * (1 - spared)
