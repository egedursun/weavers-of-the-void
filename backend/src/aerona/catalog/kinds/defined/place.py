from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.place import PlaceHeight

PLACE_HEIGHT = total(
    PlaceHeight,
    {
        PlaceHeight.FLAT: Defined("Flat", checked_by=(), used_by=("catalog.place_terrain.PLACE_KINDS",)),
        PlaceHeight.LOW: Defined("Low", checked_by=("catalog.place_terrain.height_of",), used_by=("catalog.place_terrain.PLACE_KINDS",)),
        PlaceHeight.HIGH: Defined("High", checked_by=("catalog.place_terrain.height_of",), used_by=("catalog.place_terrain.PLACE_KINDS",)),
    },
)
