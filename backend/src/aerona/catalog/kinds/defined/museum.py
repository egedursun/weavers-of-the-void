from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.museum import HoardKind

HOARD_KIND = total(
    HoardKind,
    {
        HoardKind.CABINET: Defined("Cabinet of curiosities", checked_by=(), used_by=("engine.museums.hoards.found_hoards", "engine.museums.hoards.restitute")),
        HoardKind.TEMPLE_TREASURY: Defined("Temple treasury", checked_by=("engine.museums.hoards.offered",), used_by=("engine.museums.hoards.HALLS",)),
        HoardKind.ROYAL_COLLECTION: Defined(
            "Royal collection",
            checked_by=("engine.museums.hoards.found_hoards", "engine.museums.hoards.gather", "engine.museums.hoards.offered"),
            used_by=("engine.museums.hoards.found_hoards",),
        ),
        HoardKind.MUSEUM: Defined("Museum", checked_by=(), used_by=("engine.museums.hoards.HALLS", "tools.son.museums.found_museum")),
        HoardKind.TROPHY_HALL: Defined("Trophy hall", checked_by=(), used_by=("engine.museums.hoards.loot",)),
    },
)
