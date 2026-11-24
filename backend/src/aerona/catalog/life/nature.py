from collections.abc import Mapping
from types import MappingProxyType

from aerona.domain.enums.cuisine import CookingMethod
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.nature import FermentKind, SymbiosisKind

CULTURED: Mapping[FermentKind, frozenset[CookingMethod]] = MappingProxyType(
    {
        FermentKind.YEAST: frozenset({CookingMethod.BAKED}),
        FermentKind.STARTER: frozenset({CookingMethod.BAKED}),
        FermentKind.MOULD: frozenset({CookingMethod.CURED, CookingMethod.FERMENTED}),
        FermentKind.LACTIC: frozenset({CookingMethod.FERMENTED, CookingMethod.PICKLED}),
        FermentKind.VINEGAR: frozenset({CookingMethod.PICKLED}),
        FermentKind.ALKALINE: frozenset({CookingMethod.FERMENTED}),
        FermentKind.WILD: frozenset({CookingMethod.FERMENTED, CookingMethod.BAKED, CookingMethod.PICKLED}),
    }
)


DRAINING_BONDS = frozenset({SymbiosisKind.PARASITISM, SymbiosisKind.AMENSALISM})
PULSE_GOODS = frozenset({CommodityKind.GRAIN, CommodityKind.TUBERS})
FOUNDED: Mapping[CookingMethod, FermentKind] = MappingProxyType(
    {
        CookingMethod.BAKED: FermentKind.STARTER,
        CookingMethod.FERMENTED: FermentKind.LACTIC,
        CookingMethod.CURED: FermentKind.MOULD,
        CookingMethod.PICKLED: FermentKind.VINEGAR,
    }
)
