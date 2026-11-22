from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.agrarian import CommonsKind, LandUseRing, PerennialKind, PreparednessKind
from aerona.domain.enums.intervention import Disaster

SHIELDS: dict[Disaster, frozenset[PreparednessKind]] = {
    Disaster.FLOOD: frozenset({PreparednessKind.LEVEE, PreparednessKind.SEAWALL, PreparednessKind.EVACUATION_ROUTES, PreparednessKind.WARNING_NETWORK}),
    Disaster.STORM: frozenset({PreparednessKind.SEAWALL, PreparednessKind.SHELTERS, PreparednessKind.WARNING_NETWORK}),
    Disaster.EARTHQUAKE: frozenset({PreparednessKind.DRILL, PreparednessKind.SHELTERS, PreparednessKind.EVACUATION_ROUTES}),
    Disaster.VOLCANIC_QUAKE: frozenset({PreparednessKind.DRILL, PreparednessKind.SHELTERS, PreparednessKind.EVACUATION_ROUTES}),
    Disaster.ERUPTION: frozenset({PreparednessKind.DRILL, PreparednessKind.EVACUATION_ROUTES, PreparednessKind.WARNING_NETWORK}),
    Disaster.DROUGHT: frozenset({PreparednessKind.STOCKPILE, PreparednessKind.RESERVES_OF_ENERGY}),
    Disaster.PLAGUE: frozenset({PreparednessKind.QUARANTINE_PLAN}),
}


BOOK_SHIELDS = {disaster: kinds | {PreparednessKind.WARD} for disaster, kinds in SHIELDS.items()}


KIND_TOLL: Mapping[PerennialKind, tuple[int, str, int]] = total(
    PerennialKind,
    {
        PerennialKind.ORCHARD: (100, "soil_fertility", 0),
        PerennialKind.VINEYARD: (110, "soil_fertility", 0),
        PerennialKind.GROVE: (90, "soil_fertility", 0),
        PerennialKind.TIMBER: (100, "forest_cover", 1),
        PerennialKind.PLANTATION: (150, "soil_fertility", -1),
        PerennialKind.FOREST_GARDEN: (70, "forest_cover", 1),
    },
)


COMMONS_BOON: Mapping[CommonsKind, tuple[str, int]] = total(
    CommonsKind,
    {
        CommonsKind.PASTURE: ("prosperity", 1),
        CommonsKind.WOODS: ("construction_capacity", 2),
        CommonsKind.FISHERY: ("prosperity", 1),
        CommonsKind.WATER: ("sanitation", 1),
        CommonsKind.HUNTING_GROUND: ("prosperity", 1),
        CommonsKind.QUARRY: ("construction_capacity", 3),
        CommonsKind.SPECTRUM: ("prestige", 1),
        CommonsKind.ORBITS: ("prestige", 2),
        CommonsKind.SOURCE_GROUND: ("public_order", 1),
    },
)


RING_ORDER = (LandUseRing.GARDENS, LandUseRing.FORESTRY, LandUseRing.GRAIN, LandUseRing.RANCHING, LandUseRing.WILDS)
