from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.garden import GardenKind

GARDEN_KIND = total(
    GardenKind,
    {
        GardenKind.PLEASURE: Defined("Pleasure garden", checked_by=(), used_by=("engine.museums.gardens.found_gardens",)),
        GardenKind.PHYSIC: Defined("Physic garden", checked_by=("engine.museums.reading.physic_share",), used_by=("engine.museums.gardens.LAID_OUT",)),
        GardenKind.MONASTERY: Defined("Monastery garden", checked_by=(), used_by=("engine.museums.gardens.LAID_OUT",)),
        GardenKind.PARK: Defined("Park", checked_by=(), used_by=("engine.museums.gardens.LAID_OUT",)),
        GardenKind.HUNTING_PARK: Defined("Hunting park", checked_by=("engine.museums.gardens.PLANTED",), used_by=("engine.museums.gardens.found_gardens",)),
        GardenKind.SACRED_GROVE: Defined(
            "Sacred grove",
            checked_by=("engine.museums.gardens.love_groves", "engine.protected_nature.areas.protect_rights"),
            used_by=("engine.museums.gardens.found_gardens",),
        ),
        GardenKind.CEMETERY: Defined("Cemetery", checked_by=(), used_by=("engine.museums.gardens.LAID_OUT",)),
    },
)
