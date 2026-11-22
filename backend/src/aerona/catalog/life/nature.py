from collections.abc import Mapping
from types import MappingProxyType

from aerona.domain.enums.cuisine import CookingMethod
from aerona.domain.enums.nature import FermentKind

CULTURED: Mapping[FermentKind, frozenset[CookingMethod]] = MappingProxyType(
    {
        FermentKind.YEAST: frozenset({CookingMethod.BAKED}),
        FermentKind.STARTER: frozenset({CookingMethod.BAKED}),
        FermentKind.MOULD: frozenset({CookingMethod.CURED, CookingMethod.FERMENTED}),
        FermentKind.LACTIC: frozenset({CookingMethod.FERMENTED, CookingMethod.PICKLED}),
        FermentKind.VINEGAR: frozenset({CookingMethod.PICKLED}),
    }
)


FOUNDED: Mapping[CookingMethod, FermentKind] = MappingProxyType(
    {
        CookingMethod.BAKED: FermentKind.STARTER,
        CookingMethod.FERMENTED: FermentKind.LACTIC,
        CookingMethod.CURED: FermentKind.MOULD,
        CookingMethod.PICKLED: FermentKind.VINEGAR,
    }
)
